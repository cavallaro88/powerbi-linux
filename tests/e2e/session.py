#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Bounded synthetic session. UI refresh and model/visual evidence are separate."""
import argparse
import base64
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux.common import Paths, atomic_json, Error
from pbi_linux.provision import active, BIN
from pbi_linux.launch import UNIT


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('project',type=Path)
    p.add_argument('--seconds',type=int,default=300)
    p.add_argument('--ui-refresh',action='store_true')
    p.add_argument('--sales-table',default='Table',help='Table containing the synthetic Vendas values')
    p.add_argument('--save',action='store_true',help='Save the supplied disposable project through Desktop')
    p.add_argument('--exercise-ui',action='store_true',help='Sort the synthetic visual and check values every five minutes')
    p.add_argument('--probes',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if not 90<=a.seconds<=10800:
        p.error('seconds must be 90..10800')
    from websocket import create_connection
    paths=Paths()
    installed=active(paths)
    prefix,runtime=Path(installed['prefix']),Path(installed['runtime'])
    a.output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,WINEPREFIX=str(prefix),WINEDEBUG='-all')
    for var in ('APPDOMAIN_MANAGER_ASM','APPDOMAIN_MANAGER_TYPE'):
        env.pop(var,None)
    def probe(name,*args,label=None):
        r=subprocess.run([runtime/'bin/wine',a.probes/(name+'.exe'),*map(str,args)],env=env,
                         text=True,capture_output=True,timeout=60)
        (a.output/((label or name)+'.log')).write_text(r.stdout+'\n'+r.stderr)
        if r.returncode:
            raise Error(name+' failed; no success inferred')
        return r.stdout
    def targets():
        result=[]
        for file in (prefix/'drive_c/users').glob('*/AppData/Local/Microsoft/Power BI Desktop/**/DevToolsActivePort'):
            try:
                if file.stat().st_mtime < started_wall:
                    continue
                port=int(file.read_text().splitlines()[0])
                with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/json/list',timeout=2) as r:
                    result.extend(json.load(r))
            except (OSError,ValueError,IndexError):
                continue
        return [t for t in result if t.get('type')=='page' and 'webSocketDebuggerUrl' in t]
    def cdp(page,method,params):
        with contextlib.closing(create_connection(page['webSocketDebuggerUrl'],timeout=5,suppress_origin=True)) as ws:
            ws.send(json.dumps({'id':1,'method':method,'params':params}))
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                reply=json.loads(ws.recv())
                if reply.get('id')==1:
                    if 'error' in reply:
                        raise Error(str(reply['error']))
                    return reply.get('result',{})
            raise Error('CDP response timed out')
    def native_windows():
        reply=subprocess.run([runtime/'bin/wine',a.probes/'ui-probe.exe','windows'],env=env,
                             text=True,capture_output=True,timeout=8)
        if reply.returncode:
            raise Error('Native window enumeration failed')
        return [line for line in reply.stdout.splitlines()
                if line.startswith('WINDOW ') and 'owned=0' in line
                and 'class=WindowsForms10.Window.8.' in line]
    def native_capture(label):
        from PIL import Image
        windows=native_windows()
        if len(windows)!=1:
            raise Error('Expected one native document window for frame evidence')
        hwnd=windows[0].split('hwnd=',1)[1].split()[0]
        file=paths.state/'diagnostic-captures'/('wayland-%08x.bmp'%int(hwnd,16))
        if not file.exists() or file.stat().st_mtime<started_wall:
            raise Error('The native document has no current submitted Wayland frame')
        Image.open(file).save(a.output/(label+'.png'))
        result.setdefault('native_frames',[]).append(label+'.png')
        result.setdefault('native_frame_metadata',[]).append({
            'file':label+'.png','hwnd':hwnd,
            'source_mtime':file.stat().st_mtime,
            'source_age_seconds':round(time.time()-file.stat().st_mtime,3),
            'window':windows[0]})
    result={'schema':1,'runtime_sha256':installed['runtime_sha256'],
            'ui_refresh_requested':False,'model_total_verified':False,
            'visual_certified':False,'save_reopen_certified':False,'samples':[]}
    # Never stop an existing user session or adopt a session we did not start.
    existing=subprocess.run(['systemctl','--user','is-active','--quiet',UNIT]).returncode==0
    if existing:
        raise Error('Close the existing managed session before running a destructive developer test')
    owned=False
    started_wall=time.time()
    expected={}
    expectation=a.project.parent/'expected.json'
    if expectation.exists():
        expected=json.loads(expectation.read_text())
    try:
        subprocess.run([sys.executable,'-m','pbi_linux','open','--diagnostics',str(a.project.resolve())],
                       env={**os.environ,'PYTHONPATH':str(ROOT/'src')},check=True,timeout=30)
        owned=True
        deadline=time.monotonic()+a.seconds
        page=None
        next_process_sample=0
        previous_gpu_pids=None
        result['gpu_restart_events']=[]
        result['ui_checkpoints']=[]
        next_ui_check=time.monotonic()+60
        signal.signal(signal.SIGTERM,lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
        while time.monotonic()<deadline:
            pages=targets()
            if pages:
                page=next((t for t in pages if 'report' in t.get('url','').lower()),pages[0])
            if page and a.ui_refresh and not result['ui_refresh_requested']:
                try:
                    expression="""(()=>{
                        document.querySelectorAll('button.close-btn[data-testid=close-btn],button.glyphicon.pbi-glyph-close.glyph-mini').forEach(e=>{if(e.getBoundingClientRect().height>0)e.click()});
                        const item=document.querySelector('button[data-unique-id=Ribbon-refreshSchemaAndData]');
                        if(item&&item.getBoundingClientRect().height>0&&item.getAttribute('aria-disabled')!=='true'){item.click();return 'requested'}
                        const b=document.querySelector('[data-unique-id=Ribbon-refreshQueriesSplit][role=button] button.splitMenuButton');
                        if(!b||b.disabled||b.getAttribute('aria-disabled')==='true')return 'waiting';
                        const r=b.getBoundingClientRect(),t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
                        if(r.width<=0||r.height<=0||!t||!b.contains(t))return 'waiting';
                        b.click();return 'menu';
                    })()"""
                    answer=cdp(page,'Runtime.evaluate',{'expression':expression,'returnByValue':True})
                    result['ui_refresh_requested']=answer.get('result',{}).get('value')=='requested'
                    if result['ui_refresh_requested']:
                        result['ui_refresh_seconds']=round(time.time()-started_wall,2)
                except Exception as exc:
                    result.setdefault('ui_refresh_retries',[]).append(str(exc))
            if page and a.exercise_ui and time.monotonic()>=next_ui_check:
                answer=cdp(page,'Runtime.evaluate',{'expression':"""(()=>{
                    const header=[...document.querySelectorAll('[role=columnheader]')].find(e=>e.innerText.trim()==='Produto');
                    if(!header)return {clicked:false};header.click();
                    const values=[...document.querySelectorAll('[role=gridcell]')].map(e=>e.innerText.trim());
                    return {clicked:true,values};
                })()""",'returnByValue':True})
                checkpoint=answer.get('result',{}).get('value',{})
                if not checkpoint.get('clicked') or not all(v in checkpoint.get('values',[]) for v in ('Cafe','120','Cha','80','Suco','100','Total','300')):
                    raise Error('The synthetic visual did not remain usable during the soak')
                result['ui_checkpoints'].append({'elapsed_seconds':round(time.time()-started_wall,2),'values_verified':True})
                next_ui_check=time.monotonic()+300
            group=subprocess.run(['systemctl','--user','show',UNIT,'-p','ControlGroup','--value'],text=True,capture_output=True).stdout.strip()
            if not group or group=='/':
                raise Error('Managed session exited during the test')
            cgroup=Path('/sys/fs/cgroup')/group.lstrip('/')
            sample={'seconds_left':round(deadline-time.monotonic())}
            for metric in ('memory.current','memory.swap.current','memory.events'):
                try:sample[metric]=(cgroup/metric).read_text().strip()
                except OSError:pass
            if any(int(line.split()[1]) for line in sample.get('memory.events','').splitlines()
                   if line.startswith(('oom ','oom_kill '))):
                raise Error('The session recorded a cgroup OOM event')
            if time.monotonic()>=next_process_sample:
                next_process_sample=time.monotonic()+30
                processes=[]
                try:
                    for pid in (cgroup/'cgroup.procs').read_text().split():
                        proc=Path('/proc')/pid
                        try:
                            command=(proc/'cmdline').read_bytes()
                            role='gpu' if b'--type=gpu-process' in command else 'renderer' if b'--type=renderer' in command else 'other'
                            pss=next(line.split()[1] for line in (proc/'smaps_rollup').read_text().splitlines() if line.startswith('Pss:'))
                            processes.append({'pid':int(pid),'role':role,'pss_kib':int(pss)})
                        except (OSError,StopIteration):
                            pass
                except OSError:
                    pass
                sample['processes']=processes
                gpu_pids={p['pid'] for p in processes if p['role']=='gpu'}
                if previous_gpu_pids is not None and previous_gpu_pids-gpu_pids:
                    result['gpu_restart_events'].append({'elapsed_seconds':round(time.time()-started_wall,2),
                                                        'exited_pids':sorted(previous_gpu_pids-gpu_pids)})
                if gpu_pids:
                    previous_gpu_pids=gpu_pids
                if page:
                    try:
                        # Domain enablement belongs to a CDP connection. Our
                        # bounded calls use separate connections, so use the
                        # Runtime query that needs no persistent enablement.
                        heap=cdp(page,'Runtime.getHeapUsage',{})
                        sample['js_heap']={'used_bytes':heap['usedSize'],'total_bytes':heap['totalSize'],
                                           'embedder_bytes':heap.get('embedderHeapUsedSize',0),
                                           'backing_bytes':heap.get('backingStorageSize',0)}
                    except Exception as exc:
                        sample['heap_sample_error']=str(exc)
                atomic_json(a.output/'progress.json',{'elapsed_seconds':round(time.time()-started_wall,2),
                    'ui_refresh_requested':result['ui_refresh_requested'],'sample':sample})
            result['samples'].append(sample)
            time.sleep(2)
        ports=list((prefix/'drive_c/users').glob('*/AppData/Local/Microsoft/Power BI Desktop/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt'))
        if not ports:
            raise Error('No Analysis Services workspace port found')
        raw=max(ports,key=lambda f:f.stat().st_mtime).read_bytes()
        port=raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8-sig').strip('\ufeff\x00 \r\n')
        listing=probe('refresh-probe',port,'--list')
        result['model_listing']=listing.strip()
        if expected:
            expected_tables=expected['tables']
            if 'tables='+str(expected_tables) not in listing:
                raise Error('Synthetic model table count differs from expectation')
        dax=probe('adomd-probe',port,"EVALUATE ROW(\"Total\", SUM('"+a.sales_table.replace("'","''")+"'[Vendas]))")
        result['model_total_verified']=any(line.strip()=='COL0: 300' for line in dax.splitlines())
        expect_data=a.ui_refresh or expected.get('data_loaded',True)
        result['model_expected_empty']=not expect_data
        result['model_empty_verified']=any(line.strip()=='COL0:' for line in dax.splitlines())
        if expect_data and expected.get('fact_rows') and expected.get('tables',1)>1:
            # A populated sales table alone cannot prove that all 158 tables
            # finished refreshing. Verify every synthetic fact table as well.
            names=expected.get('fact_tables') or ['Fact%03d'%i for i in range(1,expected['tables'])]
            count=len(names)
            query='EVALUATE ROW('+','.join(
                '"Rows%03d", COUNTROWS(\'%s\')'%(i,name)
                for i,name in enumerate(names))+')'
            rows=probe('adomd-probe',port,query,label='fact-rowcounts')
            lines={line.strip() for line in rows.splitlines()}
            result['fact_rows_verified']=all(
                'COL%d: %d'%(i,expected['fact_rows']) in lines for i in range(count))
            if not result['fact_rows_verified']:
                raise Error('Not all synthetic fact tables contain their expected rows')
            if expected.get('relationships'):
                query="EVALUATE ROW(\"RelatedAmount\", CALCULATE(SUM('Fact001'[Amount]), 'Dimension'[Id] = 1))"
                related=probe('adomd-probe',port,query,label='relationship-filter')
                result['relationship_filter_verified']=any(line.strip()=='COL0: 1' for line in related.splitlines())
                if not result['relationship_filter_verified']:
                    raise Error('The synthetic dimension filter did not reach the fact table')
        pages=targets()
        if not pages:
            raise Error('CDP page unavailable at final capture; inspect native captures for UI state')
        page=next((t for t in pages if 'report' in t.get('url','').lower()),pages[0])
        # Preserve the driver's sample before browser screenshot instrumentation.
        # The diagnostic hook samples at most every 500 ms; it is not a record
        # of every submitted buffer and must still be reviewed independently.
        native_capture('native-before-save' if a.save else 'native-final')
        shot=cdp(page,'Page.captureScreenshot',{'format':'png'})
        (a.output/'report.png').write_bytes(base64.b64decode(shot['data']))
        if expect_data and not result['model_total_verified']:
            raise Error('Expected synthetic total 300 not observed')
        if not expect_data and not result['model_empty_verified']:
            raise Error('Expected a definitions-only model without imported data')
        if a.ui_refresh and not result['ui_refresh_requested']:
            raise Error('Refresh button was not exercised; no UI success inferred')
        if a.save:
            saved_at=time.time()
            answer=cdp(page,'Runtime.evaluate',{'expression':
                "(()=>{const b=document.querySelector('button[aria-label=Save]');if(!b||b.disabled)return false;b.click();return true})()",'returnByValue':True})
            if answer.get('result',{}).get('value') is not True:
                raise Error('Save button unavailable')
            save_deadline=time.monotonic()+60
            root=a.project.parent.parent if a.project.suffix.lower()=='.pbir' else a.project.parent
            while time.monotonic()<save_deadline:
                candidates=[a.project] if a.project.suffix.lower()=='.pbix' else list(root.rglob('cache.abf'))
                updated=[f for f in candidates if f.exists() and f.stat().st_size>0 and f.stat().st_mtime>=saved_at-1]
                windows=native_windows()
                if updated and windows and all('enabled=1' in w for w in windows):
                    result['save_observed']=True
                    result['saved_files']=[str(f.relative_to(root)) for f in updated]
                    # A model-cache mtime alone can precede the end of Save's
                    # temporary native overlay. Let the window repaint before
                    # recording the post-save surface.
                    time.sleep(3)
                    native_capture('native-after-save')
                    if expectation.exists() and expect_data and result['model_total_verified']:
                        # This metadata belongs to the disposable generated fixture.
                        # A reopen must now expect the data Desktop actually saved.
                        atomic_json(expectation,{**expected,'data_loaded':True})
                    break
                time.sleep(1)
            else:
                raise Error('Desktop Save did not produce an updated report or model cache')
        result['backend_evidence_complete']=True
    except BaseException as exc:
        result['error']=type(exc).__name__+': '+str(exc)
    finally:
        result['elapsed_seconds']=round(time.time()-started_wall,2)
        captures=paths.state/'diagnostic-captures'
        if captures.exists():
            from PIL import Image
            for file in captures.glob('*.bmp'):
                if file.stat().st_mtime >= started_wall:
                    try:
                        Image.open(file).save(a.output/(file.stem+'.png'))
                    except OSError:
                        pass
        atomic_json(a.output/'result.json',result)
        if owned:
            try:
                ui=a.probes/'ui-probe.exe'
                if ui.exists():
                    closing=subprocess.run([runtime/'bin/wine',ui,'close-pbi'],env=env,
                                           text=True,capture_output=True,timeout=8)
                    (a.output/'close.log').write_text(closing.stdout+closing.stderr)
                    time.sleep(3)
                subprocess.run(['systemctl','--user','stop',UNIT],timeout=35,check=True)
            except subprocess.SubprocessError:
                result['teardown_error']='Service stop failed or exceeded its deadline'
                atomic_json(a.output/'result.json',result)
    print(a.output/'result.json')
    return 1 if result.get('error') or result.get('teardown_error') else 0

if __name__=='__main__':
    raise SystemExit(main())
