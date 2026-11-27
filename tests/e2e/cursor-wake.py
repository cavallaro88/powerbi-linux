#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that Desktop's UI thread keeps answering after a slow cursor lookup.

Needs a disposable session started with `pbi-linux open --diagnostics` and a
report open. The browser is made to select a cursor that is not a shared system
cursor; Wine's cursor is parked on the caption area and moved back over the
page while the browser process is stopped for a moment, so the UI thread's
lookup of that cursor times out. The UI thread must still answer a sent message
afterwards. Only Wine's own cursor moves (SendInput); the report is not touched.

The Wayland driver looks a cursor up only while the desktop pointer is over the
Desktop window, so leave the pointer resting there. The test fails, rather than
passing, when the session log shows that no lookup took place.
"""
import argparse
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
from pbi_linux.common import Paths, Error, wine_env
from pbi_linux.provision import active


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probes',type=Path,required=True,help='Directory with the compiled cursor-wake-probe.exe')
    p.add_argument('--cursor',default='col-resize',help='CSS cursor that Chromium draws itself')
    p.add_argument('--rounds',type=int,default=3)
    p.add_argument('--stall-ms',type=int,default=400,help='How long the cursor owner is stopped; 0 leaves it running')
    a=p.parse_args()
    probe_exe=a.probes/'cursor-wake-probe.exe'
    if not probe_exe.is_file():
        p.error('Compile tests/e2e/cursor-wake-probe.cs into --probes first')
    from websocket import create_connection
    installed=active(Paths())
    prefix,runtime=Path(installed['prefix']),Path(installed['runtime'])
    # The installation's own Wine: a shell's WINESERVER or WINELOADER is dropped.
    env=dict(wine_env(prefix),WINEDEBUG='-all')
    def page():
        for file in (prefix/'drive_c/users').glob('*/AppData/Local/Microsoft/Power BI Desktop/**/DevToolsActivePort'):
            try:
                port=int(file.read_text().splitlines()[0])
                with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/json/list',timeout=2) as r:
                    for target in json.load(r):
                        if target.get('type')=='page' and 'reportView' in target.get('url',''):
                            return target
            except (OSError,ValueError,IndexError):
                continue
        raise Error('No diagnostics session with a report view was found')
    def evaluate(expression):
        with contextlib.closing(create_connection(page()['webSocketDebuggerUrl'],timeout=10,suppress_origin=True)) as ws:
            ws.send(json.dumps({'id':1,'method':'Runtime.evaluate','params':{'expression':expression,'returnByValue':True}}))
            while True:
                reply=json.loads(ws.recv())
                if reply.get('id')==1:
                    return reply.get('result',{}).get('result',{}).get('value')
    def probe(*args):
        r=subprocess.run([runtime/'bin/wine',probe_exe,*map(str,args)],env=env,text=True,capture_output=True,timeout=60)
        # ping exits 1 for an unanswered message; anything else (2: the window was
        # not found, or a dialog disables it) means the round could not be measured.
        if r.returncode and not (args[2]=='ping' and r.returncode==1):
            raise Error('Probe could not run %s: %s' % (args[2],r.stdout.strip() or 'no output'))
        return r.returncode,r.stdout.strip()
    def lookups():
        try:
            return (Paths().state/'session.log').read_bytes().count(b'Failed to get icon info')
        except OSError:
            return 0
    def browser():
        for entry in Path('/proc').iterdir():
            if entry.name.isdigit():
                try:
                    command=(entry/'cmdline').read_bytes()
                except OSError:
                    continue
                if b'msedgewebview2.exe' in command and b'--embedded-browser-webview' in command and b'--type=' not in command:
                    return int(entry.name)
        raise Error('WebView2 browser process not found')
    width,height=evaluate('[innerWidth, innerHeight]')
    size=(width,height)
    code,text=probe(*size,'ping',3000)
    if code:
        raise Error('UI thread unusable before the test: '+text)
    style="(() => { let s = document.getElementById('pbi-cursor-wake'); if (!s) { s = document.createElement('style'); s.id = 'pbi-cursor-wake'; document.head.appendChild(s); } s.textContent = '* { cursor: %s !important; }'; return true; })()"
    failures=0
    before=lookups()
    try:
        evaluate(style % a.cursor)
        for number in range(1,a.rounds+1):
            probe(*size,'move',width//2,height//2)
            time.sleep(.4)
            probe(*size,'park')
            time.sleep(.4)
            pid=browser()
            if a.stall_ms:
                os.kill(pid,signal.SIGSTOP)
            try:
                probe(*size,'move',width//2+number*7,height//2)
                time.sleep(a.stall_ms/1000)
            finally:
                os.kill(pid,signal.SIGCONT)
            time.sleep(1)
            code,text=probe(*size,'ping',3000)
            print('round',number,text,flush=True)
            failures+=bool(code)
            probe(*size,'park')   # an internal cursor message wakes a deaf UI thread
            time.sleep(.3)
    finally:
        evaluate("(() => { const s = document.getElementById('pbi-cursor-wake'); if (s) s.remove(); return true; })()")
    exercised=lookups()-before
    if failures:
        raise Error('UI thread stopped answering in %d of %d rounds' % (failures,a.rounds))
    if not exercised:
        raise Error('Not exercised: no cursor lookup was logged. Rest the desktop pointer over the Desktop window')
    print('PASS: the UI thread answered in %d rounds with %d cursor lookups logged' % (a.rounds,exercised))


if __name__=='__main__':
    try:
        main()
    except Error as exc:
        print('FAILED:',exc,file=sys.stderr)
        sys.exit(1)
