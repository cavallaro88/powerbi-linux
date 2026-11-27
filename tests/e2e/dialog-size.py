#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that a legacy HTML dialog gets the size its page asks for.

Needs a disposable session started with `pbi-linux open --diagnostics` and a
report open. By default the test sends the report page's error message to the
host with one argument missing, which makes Desktop open its own unexpected
error report ("Something went wrong"), a borderless owned dialog that starts at
2 x 2 pixels and resizes itself once its page has been measured. With
--button the test presses a ribbon button by its accessible name instead, for
example "Data source settings" with --title "Data source settings".

The dialog must reach a usable size and must not be marked maximized. It is
then closed with WM_CLOSE; nothing is submitted and the report is not changed.
"""
import argparse
import contextlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux.common import Paths, Error, wine_env
from pbi_linux.provision import active

TRIGGER='''(() => { window.chrome.webview.postMessage({objectId: "BrowserInternalContext", method: "OnError",
  promiseHandle: 900000 + (Date.now() % 90000), args: ["dialog size test " + Date.now(), "at test (test:1:1)"]}); return true; })()'''
PRESS='''(() => { const name = %s; const found = [...document.querySelectorAll("button,[role=button],[role=menuitem]")]
  .filter(e => (e.getAttribute("aria-label") || e.textContent || "").trim() === name); if (!found.length) return false;
  found[0].click(); return true; })()'''


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--probes',type=Path,required=True,help='Directory with the compiled dialog-size-probe.exe')
    p.add_argument('--title',default='Something went wrong',help='Text in the dialog title')
    p.add_argument('--button',help='Accessible name of a ribbon button that opens the dialog')
    p.add_argument('--min-width',type=int,default=300)
    p.add_argument('--min-height',type=int,default=150)
    p.add_argument('--seconds',type=float,default=15)
    a=p.parse_args()
    probe_exe=a.probes/'dialog-size-probe.exe'
    if not probe_exe.is_file():
        p.error('Compile tests/e2e/dialog-size-probe.cs into --probes first')
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
    def probe(command):
        r=subprocess.run([runtime/'bin/wine',probe_exe,command,a.title],env=env,text=True,capture_output=True,timeout=60)
        return r.returncode,r.stdout.strip()
    if probe('find')[0]==0:
        raise Error('A window titled %r is already open' % a.title)
    if not evaluate(PRESS % json.dumps(a.button) if a.button else TRIGGER):
        raise Error('The dialog could not be requested')
    deadline=time.monotonic()+a.seconds
    seen,text=False,''
    try:
        while time.monotonic()<deadline:
            code,text=probe('find')
            if code==0:
                seen=True
                width,height=map(int,text.split()[2].split('x'))
                if width>=a.min_width and height>=a.min_height and 'maximized=0' in text:
                    print('PASS:',a.title,text)
                    return
            time.sleep(.5)
    finally:
        if seen:
            probe('close')
    if not seen:
        raise Error('No window titled %r appeared within %g seconds' % (a.title,a.seconds))
    raise Error('The dialog did not reach %dx%d: %s' % (a.min_width,a.min_height,text))


if __name__=='__main__':
    try:
        main()
    except Error as exc:
        print('FAILED:',exc,file=sys.stderr)
        sys.exit(1)
