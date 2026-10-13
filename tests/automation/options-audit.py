#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Audit an already open synthetic Options dialog through the test-only manager.

Navigates tabs, checks layout and collects errors. Does not submit settings.
A passed result certifies these assertions, not physical pointer delivery.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import stat
import time
import uuid


class Bridge:
    def __init__(self, directory, timeout=12):
        self.directory = Path(directory).resolve()
        info = self.directory.stat()
        if not self.directory.is_dir() or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError('Bridge must be an existing private directory owned by this user')
        for name in ('request.txt', 'response.txt', 'inspect.js', 'audit.lock'):
            if (self.directory / name).is_symlink():
                raise RuntimeError('Bridge files must not be symlinks')
        self.timeout = timeout

    def request(self, expression):
        nonce = uuid.uuid4().hex
        script = '(function(){return JSON.stringify({nonce:' + json.dumps(nonce) + ',value:(' + expression + ')});})()'
        self._write('inspect.js', script)
        self._write('request.txt', 'inspect')
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                reply = (self.directory / 'response.txt').read_text()
                if 'SCOPE synthetic-options' not in reply:
                    time.sleep(.1)
                    continue
                for line in reply.splitlines():
                    if not line.startswith('SCRIPT '):
                        continue
                    try:
                        value = json.loads(line[7:])
                    except ValueError:
                        continue
                    if value.get('nonce') == nonce:
                        return value['value']
            except (OSError, ValueError):
                pass
            time.sleep(.1)
        raise RuntimeError('No matching response from the synthetic Options bridge before deadline')

    def _write(self, name, value):
        temp = self.directory / ('.' + name + '-' + uuid.uuid4().hex)
        try:
            temp.write_text(value)
            temp.chmod(0o600)
            os.replace(temp, self.directory / name)
        finally:
            temp.unlink(missing_ok=True)


SNAPSHOT = r'''(function(){
    var g=KoOptionsDialog.getTabControl().viewModel, buttons=[], panes=[];
    $('.o-action-button').filter(function(){return this.innerText==='OK'||this.innerText==='Cancel';}).each(function(){
        var r=this.getBoundingClientRect();
        if(r.width&&r.height)buttons.push({text:this.innerText,inside:r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight});
    });
    KoOptionsDialog.getTabControl().panes.element.children(':visible').each(function(){
        var r=this.getBoundingClientRect();panes.push({width:r.width,height:r.height,textLength:this.innerText.length});
    });
    var e=KoOptionsDialog.getTabControl().panes.element[0],r=e.getBoundingClientRect(),body=document.querySelector('.o-group-body').getBoundingClientRect();
    return {selected:[g.selectedGroupName(),g.selectedIndex()],panes:panes,footer:buttons,
        scrollPane:{client:e.clientHeight,scroll:e.scrollHeight,overflow:getComputedStyle(e).overflowY,inside:r.bottom<=body.bottom+1},errors:window.__productOptionsAudit.errors};
})()'''


def valid_tab(result, group, index):
    scroll = result['scrollPane']
    return (result['selected'] == [group, index]
            and bool(result['panes']) and all(p['width'] > 0 and p['height'] > 0 for p in result['panes'])
            and {b['text'] for b in result['footer']} == {'OK', 'Cancel'}
            and all(b['inside'] for b in result['footer'])
            and scroll['client'] > 0 and scroll['inside']
            and (scroll['scroll'] <= scroll['client'] or scroll['overflow'] in ('auto', 'scroll'))
            and not result['errors'])


def audit(bridge, expected_tabs=22):
    catalog = bridge.request("(function(){return KoOptionsDialog.getTabControl().viewModel.groups().map(function(g){return {name:g.groupName,tabs:g.tabs().map(function(t){return {index:t.index,name:t.tabName};})};});})()")
    count = sum(len(g['tabs']) for g in catalog)
    if count != expected_tabs:
        raise RuntimeError('Unexpected tab inventory: expected %d, found %d' % (expected_tabs, count))
    # Save only navigation/error-handler state; never serialize native host objects.
    bridge.request("(function(){var g=KoOptionsDialog.getTabControl().viewModel;window.__productOptionsAudit={errors:[],old:window.onerror,group:g.selectedGroupName(),index:g.selectedIndex()};window.onerror=function(m){window.__productOptionsAudit.errors.push(String(m));return true;};return true;})()")
    results = []
    try:
        for group in catalog:
            for tab in group['tabs']:
                bridge.request('(function(){KoOptionsDialog.getTabControl().viewModel.onTabClick(' + json.dumps(group['name']) + ',' + str(tab['index']) + ');return true;})()')
                time.sleep(.2)
                result = bridge.request(SNAPSHOT)
                result.update(group=group['name'], tab=tab['name'])
                result['passed'] = valid_tab(result, group['name'], tab['index'])
                results.append(result)
                print(group['name'] + '/' + tab['name'] + ': ' + ('PASS' if result['passed'] else 'FAIL'), flush=True)
    finally:
        bridge.request("(function(){var a=window.__productOptionsAudit;KoOptionsDialog.getTabControl().viewModel.onTabClick(a.group,a.index);window.onerror=a.old;delete window.__productOptionsAudit;return true;})()")
    return {'passed': len(results) == expected_tabs and all(r['passed'] for r in results),
            'tabs_checked': len(results), 'scope': 'Synthetic tab navigation, content/footer/scroll geometry and JS errors',
            'settings_submitted': False, 'compositor_pointer_certified': False, 'results': results}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bridge', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True, help='New evidence directory')
    p.add_argument('--expected-tabs', type=int, default=22)
    args = p.parse_args()
    if args.expected_tabs < 1:
        p.error('expected-tabs must be positive')
    args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    result = {'passed': False, 'status': 'failed', 'settings_submitted': False}
    try:
        bridge = Bridge(args.bridge)
        with (bridge.directory / 'audit.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = audit(bridge, args.expected_tabs)
            result['status'] = 'passed' if result['passed'] else 'failed'
    except Exception as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    finally:
        (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(args.output / 'result.json')
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
