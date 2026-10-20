#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Open synthetic documents through GIO using the production desktop entry.

Run only with a disposable installation and isolated XDG directories. The
optional --make-default changes the test user's associations through the same
integration function as setup. This test never enables diagnostic CDP.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux import desktop
from pbi_linux.common import Paths, Error, atomic_json, digest, read_json
from pbi_linux.launch import UNIT
from pbi_linux.provision import active


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project',type=Path)
    parser.add_argument('--additional',type=Path)
    parser.add_argument('--make-default',action='store_true')
    parser.add_argument('--sales-table',default='Table')
    parser.add_argument('--probes',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    documents=[args.project.resolve()]
    if args.additional:
        documents.append(args.additional.resolve())
    if any(not f.is_file() or f.suffix.lower() not in ('.pbix','.pbip','.pbir') for f in documents):
        parser.error('Supply existing synthetic PBIX/PBIP/PBIR files')
    paths=Paths();installed=active(paths)
    args.output.mkdir(parents=True,exist_ok=False)
    result={'runtime_sha256':installed['runtime_sha256'],'diagnostic_mode':False,'documents':[]}
    prefix,runtime=Path(installed['prefix']),Path(installed['runtime'])
    probe_env=dict(os.environ,WINEPREFIX=str(prefix),WINEDEBUG='-all')
    for name in ('APPDOMAIN_MANAGER_ASM','APPDOMAIN_MANAGER_TYPE'):
        probe_env.pop(name,None)
    owned=False;started=time.time()
    def run(command, timeout=10, env=None):
        return subprocess.run([str(v) for v in command],env=env,text=True,capture_output=True,timeout=timeout)
    def windows():
        probe=run([runtime/'bin/wine',args.probes/'ui-probe.exe','windows'],env=probe_env)
        if probe.returncode:
            raise Error('Native window enumeration failed')
        return [line for line in probe.stdout.splitlines() if line.startswith('WINDOW ')]
    def workspaces():
        root=prefix/'drive_c/users'
        return sorted(root.glob('*/AppData/Local/Microsoft/Power BI Desktop/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt'),key=lambda f:f.stat().st_mtime)
    try:
        if run(['systemctl','--user','is-active','--quiet',UNIT]).returncode==0:
            raise Error('Close the existing session before this developer test')
        if args.make_default:
            desktop.integrate(paths,make_default=True)
        entry=paths.data.parent/'applications'/desktop.DESKTOP_ID
        result['desktop_sha256']=digest(entry)
        previous_processes=set()
        for index,document in enumerate(documents):
            mime=desktop.MIMES[('.pbix','.pbip','.pbir').index(document.suffix.lower())]
            info=run(['gio','info','--attributes','standard::content-type',document])
            default=run(['xdg-mime','query','default',mime])
            if info.returncode or mime not in info.stdout:
                raise Error('GIO did not recognize '+document.suffix+' as the installed Power BI MIME type')
            if default.returncode or default.stdout.strip()!=desktop.DESKTOP_ID:
                raise Error('The test profile does not select the Power BI desktop entry')
            before={str(f) for f in workspaces()}
            opened=run(['gio','open',document],timeout=30)
            if opened.returncode:
                raise Error('GIO could not dispatch the document')
            owned=True
            ready_deadline=time.monotonic()+90
            new_port=None;current=[]
            while time.monotonic()<ready_deadline:
                ports=[f for f in workspaces() if str(f) not in before and f.stat().st_mtime>=started]
                current=windows()
                candidates=[line for line in current if 'class=WindowsForms10.Window.8.' in line and 'owned=0' in line]
                if ports and len(candidates)>=index+1:
                    new_port=ports[-1]
                    break
                time.sleep(2)
            if not new_port:
                raise Error('Desktop did not create a workspace and document window after GIO open')
            current_processes={line.split(' owner=',1)[1].split()[0] for line in candidates}
            if not previous_processes.issubset(current_processes):
                raise Error('Opening another document replaced an earlier window')
            time.sleep(15)
            raw=new_port.read_bytes();port=raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8-sig').strip('\ufeff\x00 \r\n')
            table=args.sales_table if index==0 else 'Table'
            query='EVALUATE ROW("Total", SUM(\''+table.replace("'","''")+'\'[Vendas]))'
            dax=run([runtime/'bin/wine',args.probes/'adomd-probe.exe',port,query],timeout=60,env=probe_env)
            (args.output/('dax-'+str(index)+'.log')).write_text(dax.stdout+dax.stderr)
            if dax.returncode or 'COL0: 300' not in {line.strip() for line in dax.stdout.splitlines()}:
                raise Error('The document opened through GIO did not independently return total 300')
            for owner in current_processes:
                deadline=time.monotonic()+45
                attempts=[]
                while time.monotonic()<deadline:
                    # Desktop recreates its native HWND during startup. Keep
                    # the document process identity and rediscover its window.
                    line=next((w for w in windows() if ' owner='+owner+' ' in w and
                               'owned=0' in w and 'class=WindowsForms10.Window.8.' in w),None)
                    if not line:
                        time.sleep(1)
                        continue
                    hwnd=line.split('hwnd=',1)[1].split()[0]
                    ready=run([runtime/'bin/wine',args.probes/'ui-probe.exe','responsive',hwnd],env=probe_env)
                    attempts.append(ready.stdout+ready.stderr)
                    if not ready.returncode and 'RESPONDS 1' in ready.stdout:
                        break
                    time.sleep(2)
                else:
                    (args.output/('responsive-'+str(index)+'.log')).write_text(''.join(attempts))
                    raise Error('A document window does not respond after initialization')
                (args.output/('responsive-'+str(index)+'.log')).write_text(''.join(attempts))
            previous_processes=current_processes
            result['documents'].append({'extension':document.suffix.lower(),'mime':mime,'dax_total':300,'native_windows_respond':True})
            atomic_json(args.output/'progress.json',result)
        group=run(['systemctl','--user','show',UNIT,'-p','ControlGroup','--value']).stdout.strip()
        if not group or group=='/':raise Error('Managed session exited unexpectedly')
        cgroup=Path('/sys/fs/cgroup')/group.lstrip('/')
        result['memory_peak_bytes']=int((cgroup/'memory.peak').read_text())
        result['memory_max_bytes']=(cgroup/'memory.max').read_text().strip()
        result['swap_max_bytes']=(cgroup/'memory.swap.max').read_text().strip()
        result['swap_current_bytes']=int((cgroup/'memory.swap.current').read_text())
        result['memory_events']=(cgroup/'memory.events').read_text()
        result['normal_mode_confirmed']=True
        for pid in (cgroup/'cgroup.procs').read_text().split():
            try:
                env=(Path('/proc')/pid/'environ').read_bytes().split(b'\0')
                command=(Path('/proc')/pid/'cmdline').read_bytes()
                if b'PBI_DIAGNOSTICS=1' in env or b'--remote-debugging-port' in command:
                    result['normal_mode_confirmed']=False
            except OSError:
                pass
        if not result['normal_mode_confirmed']:raise Error('Desktop launch enabled diagnostics unexpectedly')
        if any(int(line.split()[1]) for line in result['memory_events'].splitlines() if line.startswith(('oom ','oom_kill '))):
            raise Error('OOM occurred during normal desktop opening')
        result['passed']=True
    except Exception as exc:
        result['error']=type(exc).__name__+': '+str(exc)
    finally:
        if owned:
            try:
                run(['systemctl','--user','stop',UNIT],timeout=35)
            except subprocess.TimeoutExpired:
                result['teardown_error']='Service stop exceeded its deadline'
        result['elapsed_seconds']=round(time.time()-started,2)
        atomic_json(args.output/'result.json',result)
    print(args.output/'result.json')
    return 0 if result.get('passed') and not result.get('teardown_error') else 1


if __name__=='__main__':
    raise SystemExit(main())
