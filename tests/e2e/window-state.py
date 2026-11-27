#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that a tiling compositor's configure events leave a window tiled and maximized.

Hyprland only: the test reads and moves its own windows with hyprctl. It opens
small test windows on the focused workspace for a few seconds (--workspace
moves them to another visible workspace once they are mapped) and needs no
Desktop session. The second case needs a workspace with no other tiled window,
and a hidden workspace on the same monitor.

1. A window that starts maximized while a floating window holds the focus must
   be mapped as a tile, not as a floating window of the size of the monitor.
2. A tiled window must keep its maximized style and its size while its
   workspace is hidden and after it is shown again.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux.common import Paths, Error, wine_env
from pbi_linux.provision import active

TITLE='pbi-window-state-probe'
HELPER='pbi-window-state-helper'


def clients():
    reply=subprocess.run(['hyprctl','clients','-j'],text=True,capture_output=True,timeout=10)
    try:
        return json.loads(reply.stdout)
    except ValueError:
        raise Error('hyprctl did not list the windows')


def window(title=TITLE):
    return next((c for c in clients() if c.get('title')==title),None)


def move(address,workspace):
    # Hyprland with a Lua configuration takes the dispatcher through eval;
    # older versions take the classic dispatcher. Use whichever moves the window.
    lua='hl.dispatch(hl.dsp.window.move({ workspace = "%s", follow = false, window = "address:%s" }))' % (workspace,address)
    for command in (['hyprctl','eval',lua],['hyprctl','dispatch','movetoworkspacesilent','%s,address:%s' % (workspace,address)]):
        subprocess.run(command,text=True,capture_output=True,timeout=10)
        deadline=time.monotonic()+2
        while time.monotonic()<deadline:
            found=next((c for c in clients() if c['address']==address),None)
            if found and str(found['workspace']['id'])==str(workspace):
                return
            time.sleep(.1)
    raise Error('The test window could not be moved to workspace %s' % workspace)


class Probe:
    def __init__(self,wine,exe,env,arguments):
        self.states=[]
        self.process=subprocess.Popen([wine,exe,*arguments],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        threading.Thread(target=self.read,daemon=True).start()
    def read(self):
        for line in self.process.stdout:
            if line.startswith('STATE '):
                self.states.append(line.split())
    def appear(self,seconds=30,title=TITLE,condition=lambda found:True):
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            found=window(title)
            if found and condition(found):
                return found
            if self.process.poll() is not None:
                break
            time.sleep(.1)
        raise Error('The %s window did not appear' % title)
    def state(self):
        if not self.states:
            raise Error('The probe reported no window state')
        return self.states[-1][1],self.states[-1][3]
    def settle(self,seconds=8):
        # Every tile is reported as maximized by Hyprland; wait for the driver to mirror it.
        deadline=time.monotonic()+seconds
        while time.monotonic()<deadline:
            if self.states and self.states[-1][1]=='maximized':
                time.sleep(1)
                return self.state()
            time.sleep(.1)
        raise Error('The test window was not reported as maximized: %s' % (self.states[-1:] or 'no state'))
    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.process.kill()


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--probes',type=Path,required=True,help='Directory with the compiled window-state-probe.exe')
    p.add_argument('--hidden-workspace',default='98',help='A workspace that is not shown on any monitor')
    p.add_argument('--workspace',help='A workspace shown on a monitor: move the test windows there once they are mapped')
    a=p.parse_args()
    exe=a.probes/'window-state-probe.exe'
    if not exe.is_file():
        p.error('Compile tests/e2e/window-state-probe.cs into --probes first')
    if not shutil.which('hyprctl') or not os.environ.get('HYPRLAND_INSTANCE_SIGNATURE'):
        raise Error('This test needs a Hyprland session')
    if window():
        raise Error('A window titled %r is already open' % TITLE)
    installed=active(Paths())
    wine=Path(installed['runtime'])/'bin/wine'
    # The installation's own Wine: a shell's WINESERVER or WINELOADER is dropped.
    env=dict(wine_env(installed['prefix']),WINEDEBUG='-all')
    failures=[]

    probe=Probe(wine,exe,env,['maximized','12','after-fixed'])
    try:
        # The case only means something if the fixed dialog floats and holds the
        # focus when the maximized window asks for its place.
        try:
            probe.appear(title=HELPER,
                                condition=lambda found:found['floating'] and found.get('focusHistoryID')==0)
        except Error:
            raise Error('setup: the fixed helper window did not float with the focus: %s' % window(HELPER))
        first=probe.appear()
        if window(HELPER) is None:
            raise Error('setup: the fixed helper window closed before the test window mapped')
        if a.workspace:
            for found in (first,window(HELPER)):
                if found:
                    move(found['address'],a.workspace)
        time.sleep(3)
        later=window() or first
        text='floating=%s size=%s, then floating=%s size=%s' % (first['floating'],first['size'],later['floating'],later['size'])
        try:
            reported=probe.settle()
        except Error as exc:
            reported=None
            failures.append('maximized start lost its maximized style: %s' % exc)
        if first['floating'] or later['floating']:
            failures.append('maximized start mapped floating: '+text)
        elif reported:
            print('PASS: maximized start beside a focused floating window is tiled:',
                  text+', probe %s %s' % reported)
    finally:
        probe.close()

    probe=Probe(wine,exe,env,['normal','20'])
    try:
        found=probe.appear()
        home=a.workspace or found['workspace']['id']
        if a.workspace:
            move(found['address'],a.workspace)
            found=next((c for c in clients() if c['address']==found['address']),found)
        # Alone on the hidden workspace, the window gets that workspace's whole
        # area: the sizes compare only if it was alone at home too.
        others=[c for c in clients() if str(c['workspace']['id'])==str(home)
                and c['address']!=found['address'] and not c['floating']]
        if others:
            raise Error('workspace %s holds %d other tiled window(s): pass --workspace with an empty one'
                        % (home,len(others)))
        before=probe.settle()
        try:
            move(found['address'],a.hidden_workspace)
            time.sleep(2)
            hidden=probe.state()
            moved=next((c for c in clients() if c['address']==found['address']),None)
            if moved and moved['monitor']!=found['monitor']:
                raise Error('workspace %s is on another monitor, so the tile size differs: '
                            'bind it to monitor %s with a workspace rule' % (a.hidden_workspace,found['monitor']))
        finally:
            move(found['address'],home)
        time.sleep(2)
        shown=probe.state()
        text='visible %s %s, hidden %s %s, visible again %s %s' % (*before,*hidden,*shown)
        if hidden!=before or shown!=before:
            failures.append('window changed while its workspace was hidden: '+text)
        else:
            print('PASS: window kept its state and size across a hidden workspace:',text)
    finally:
        probe.close()
    if failures:
        raise Error('; '.join(failures))


if __name__=='__main__':
    try:
        main()
    except Error as exc:
        print('FAILED:',exc,file=sys.stderr)
        sys.exit(1)
