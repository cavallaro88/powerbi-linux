#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Text/CSV Load/apply: bounded automation of the modern Get Data dialog.

Opens a blank report and the Get Data menu's Text/CSV entry, sets the supplied
CSV path, clicks Load and verifies the table in the model. The optional
all-sources route diagnoses the general chooser and its OneLake sign-in popup.
Automatic teardown at the end.

Use: python3 tests/e2e/csv-session.py CSV --probes DIR --output NEW_DIR
"""
import base64
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from pbi_linux.common import Paths, Error
from pbi_linux.provision import active
from pbi_linux.launch import UNIT
import argparse, contextlib, urllib.request
from types import SimpleNamespace
from websocket import create_connection
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('csv',type=Path)
parser.add_argument('--probes',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--entry',choices=('ribbon','all-sources'),default='ribbon',
                    help='Direct Text/CSV menu, or the general source chooser')
parser.add_argument('--save-report',type=Path,
                    help='Create a table visual and save a new synthetic PBIX here')
a=parser.parse_args()
if not a.csv.is_file():parser.error('CSV must exist')
if a.save_report:
 a.save_report=a.save_report.resolve()
 if a.save_report.suffix.lower()!='.pbix' or a.save_report.exists():
  parser.error('save-report must be a new PBIX path')
 a.save_report.parent.mkdir(parents=True,exist_ok=True)
paths=Paths();installation=active(paths)
prefix,runtime=Path(installation['prefix']),Path(installation['runtime'])
csv_path='Z:'+str(a.csv.resolve()).replace('/','\\')
table=a.csv.stem
out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
captures=paths.state/'diagnostic-captures'
env=dict(os.environ)
probe_env=dict(env,WINEPREFIX=str(prefix),WINEDEBUG='-all')
for var in ('DISPLAY','XAUTHORITY','APPDOMAIN_MANAGER_ASM','APPDOMAIN_MANAGER_TYPE'):
 probe_env.pop(var,None)
probe=[str(runtime/'bin/wine'),str(a.probes.resolve()/'ui-probe.exe')]
def run(command,timeout,environment=None):
 return subprocess.run(command,env=environment,text=True,capture_output=True,timeout=timeout)
def cdp(page,method,params):
 with contextlib.closing(create_connection(page['webSocketDebuggerUrl'],timeout=8,suppress_origin=True)) as ws:
  ws.send(json.dumps({'id':1,'method':method,'params':params}))
  while True:
   reply=json.loads(ws.recv())
   if reply.get('id')==1:
    if 'error' in reply:raise RuntimeError(str(reply['error']))
    return reply.get('result',{})
d=SimpleNamespace(run=run,cdp=cdp,urlopen=urllib.request.urlopen)

events = []
owned = False
invocation = None
failure = None
group = None
opened_at = None
loaded = False
visual_values_verified = False
saved = False
main_id = None
main_text = ''
peak_memory = 0
started = time.monotonic()
started_wall = time.time()


def pages():
    result = []
    seen = set()
    users = prefix / 'drive_c/users'
    for file in users.glob('*/AppData/Local/Microsoft/Power BI Desktop/**/DevToolsActivePort'):
        try:
            port = int(file.read_text().splitlines()[0])
        except (OSError, ValueError, IndexError):
            continue
        if port in seen:
            continue
        seen.add(port)
        try:
            result.extend(json.load(d.urlopen('http://127.0.0.1:' + str(port) + '/json/list', timeout=1)))
        except Exception:
            pass
    return result


def page_with(selector):
    return next((p for p in pages() if p['type'] == 'page' and selector in p['url']), None)


def window_lines():
    try:
        text = d.run(probe + ['windows'], 8, probe_env).stdout
    except subprocess.TimeoutExpired:
        return []
    lines = []
    for line in text.splitlines():
        if not line.startswith('WINDOW hwnd='):
            continue
        fields = dict(part.split('=', 1) for part in line.split() if '=' in part)
        fields['title'] = line.split('title=', 1)[-1]
        fields['class'] = line.split('class=', 1)[-1].split(' title=')[0]
        lines.append(fields)
    return lines


def close_window(hwnd):
    d.run(probe + ['sendmsg', hwnd, '0x10', '0', '0'], 8, probe_env)


_popup_seen = {}


def dismiss_signin():
    windows = window_lines()
    popup = next((w for w in windows if 'Enter your email address' in w['title']), None)
    if not popup:
        _popup_seen.clear()
        return None
    first = _popup_seen.setdefault(popup['hwnd'], time.monotonic())
    if time.monotonic() - first < 10:
        return None
    close_window(popup['hwnd'])
    return {'hwnd': popup['hwnd'], 'title': popup['title']}


def ensure_dialog_enabled(deadline):
    # The OneLake sign-in popup only accepts WM_CLOSE once its page finished
    # loading; closing it early makes it stay/reappear. Wait, then verify.
    while time.monotonic() < deadline:
        windows = window_lines()
        popup = next((w for w in windows if 'Enter your email address' in w['title']), None)
        dialog = next((w for w in windows if w['title'] == 'Get Data (Power Query)'), None)
        if popup:
            first = _popup_seen.setdefault(popup['hwnd'], time.monotonic())
            if time.monotonic() - first >= 10:
                close_window(popup['hwnd'])
                time.sleep(2)
            else:
                time.sleep(1)
            continue
        _popup_seen.clear()
        if dialog and dialog.get('enabled') == '1':
            return True
        time.sleep(1)
    return False


def click_text(page, text):
    expression = '''(() => {
      const text=%s;
      const nodes=Array.from(document.querySelectorAll('*'));
      const leaf=nodes.find(e=>{
        if(e.children.length!==0 || e.textContent.trim()!==text) return false;
        const r=e.getBoundingClientRect();
        if(r.width<=0||r.height<=0) return false;
        const top=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
        return top&&(e.contains(top)||top.contains(e));
      });
      if(!leaf) return {clicked:false};
      const target=leaf.closest('button,[role="button"],[role="tab"],a')||leaf;
      if(target.disabled||target.getAttribute('aria-disabled')==='true')return {clicked:false,disabled:true};
      target.click();return {clicked:true,tag:target.tagName,text};
    })()''' % json.dumps(text)
    return d.cdp(page, 'Runtime.evaluate', {'expression': expression, 'returnByValue': True})


def set_path(page, path):
    if not page:
        raise RuntimeError('Get Data page unavailable')
    expression = '''(() => {
      const input=document.querySelector('input.ms-TextField-field');
      if(!input) return {ok:false};
      const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      setter.call(input,%s);
      input.dispatchEvent(new Event('input',{bubbles:true}));
      input.dispatchEvent(new Event('change',{bubbles:true}));
      return {ok:true,value:input.value};
    })()''' % json.dumps(path)
    return d.cdp(page, 'Runtime.evaluate', {'expression': expression, 'returnByValue': True})


def page_text(page):
    result = d.cdp(page, 'Runtime.evaluate', {
        'expression': '({ready:document.readyState,text:document.body?document.body.innerText.slice(0,4000):""})',
        'returnByValue': True})
    return result['result']['value']


def page_text_with(page, needle):
    if not page:
        return None
    try:
        state = page_text(page)
    except Exception:
        return None
    return state if needle in state['text'] else None


def record(event):
    events.append(event)
    (out / 'events.json').write_text(json.dumps(events, ensure_ascii=False, indent=2))
    print(json.dumps(event, ensure_ascii=False), flush=True)


def wait_for(condition, deadline, what):
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(1)
    raise RuntimeError('Timeout waiting for ' + what)


def click_until_state(selector, text, needle, deadline, what):
    while time.monotonic() < deadline:
        closed = dismiss_signin()
        page = page_with(selector)
        result = None
        if page:
            try:
                result = click_text(page, text)
            except Exception as exc:
                result = str(exc)
        windows = window_lines()
        print(json.dumps({'click-attempt': {'text': text, 'closed_popup': closed,
                                            'result': result,
                                            'windows': [{'title': w['title'], 'enabled': w['enabled']}
                                                        for w in windows]}}, ensure_ascii=False), flush=True)
        transition = time.monotonic() + 6
        while time.monotonic() < transition:
            dismiss_signin()
            page = page_with(selector)
            state = page_text_with(page, needle) if page else None
            if state:
                return state
            time.sleep(1)
    raise RuntimeError('Timeout waiting for ' + what)


def evaluate(page, expression):
    return d.cdp(page,'Runtime.evaluate',{'expression':expression,'returnByValue':True}).get('result',{}).get('value')


def create_visual():
    report=page_with('reportView')
    expression="""(()=>{const t=[...document.querySelectorAll('[role=treeitem]')].find(e=>e.getAttribute('aria-label')===%s);if(!t)return false;if(t.getAttribute('aria-expanded')!=='true')t.querySelector('button[data-testid=data-expand-collapse]')?.click();return true})()""" % json.dumps('Table '+table)
    if not evaluate(report,expression):
        raise RuntimeError('Imported table unavailable in the Data pane')
    if not evaluate(report,"(()=>{const b=document.querySelector('button[role=option][aria-label=Table]');b?.click();return !!b})()"):
        raise RuntimeError('Table visual button unavailable')
    for column in ('Produto','Vendas'):
        expression="""(()=>{const e=document.querySelector(%s);if(!e)return false;if(!e.checked)e.click();return e.checked})()""" % json.dumps('[data-unique-id=column_'+column+'] input[type=checkbox]')
        wait_for(lambda: evaluate(page_with('reportView'),expression),time.monotonic()+20,'visual field '+column)
    def visible_values():
        values=evaluate(page_with('reportView'),"[...document.querySelectorAll('[role=gridcell]')].map(e=>e.innerText.trim())") or []
        return values if all(v in values for v in ('Cafe','120','Cha','80','Suco','100','Total','300')) else None
    values=wait_for(visible_values,time.monotonic()+60,'rendered sales values')
    (out/'visual-values.json').write_text(json.dumps(values,ensure_ascii=False,indent=2))
    image=d.cdp(page_with('reportView'),'Page.captureScreenshot',{'format':'png'})
    (out/'visual.png').write_bytes(base64.b64decode(image['data']))
    return True


def save_report(destination):
    # Exercise Desktop's actual Save UI, rather than synthesizing a PBIX.
    report=page_with('reportView')
    if not evaluate(report,"(()=>{const b=document.querySelector('button[aria-label=Save]');b?.click();return !!b})()"):
        raise RuntimeError('Save button unavailable')
    wait_for(lambda:page_text_with(page_with('desktopDialogHost'),'Save this file'),time.monotonic()+30,'Save dialog')
    answer=click_text(page_with('desktopDialogHost'),'More options...')
    if not answer.get('result',{}).get('value',{}).get('clicked'):
        raise RuntimeError('Save location options unavailable')
    wait_for(lambda:page_text_with(page_with('reportView'),'Browse this device'),time.monotonic()+30,'local save location')
    click_text(page_with('reportView'),'Browse this device')
    dialog=wait_for(lambda:next((w for w in window_lines() if w['class']=='#32770' and w['enabled']=='1'),None),time.monotonic()+30,'native Save dialog')
    children=d.run(probe+['children',dialog['hwnd']],8,probe_env).stdout.splitlines()
    def control(kind, title=None):
        return next((line.split('hwnd=',1)[1].split()[0] for line in children
                     if 'class='+kind+' title=' in line and 'visible=1' in line
                     and (title is None or line.strip().endswith('title='+title))),None)
    edit,button=control('Edit'),control('Button','Save')
    if not edit or not button:
        raise RuntimeError('Native Save controls unavailable')
    target='Z:'+str(destination).replace('/','\\')
    typed=d.run(probe+['text',edit,target],8,probe_env)
    if typed.returncode or 'TEXT 1' not in typed.stdout:
        raise RuntimeError('Native Save filename could not be set')
    d.run(probe+['click-hwnd',button,'20','10'],8,probe_env)
    wait_for(lambda:destination.is_file() and destination.stat().st_size>0
             and not any(w['class']=='#32770' for w in window_lines()),time.monotonic()+90,'saved PBIX')
    return True


signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
try:
    if d.run(['systemctl', '--user', 'is-active', '--quiet', UNIT], 2).returncode == 0:
        raise RuntimeError('Existing session: close it before diagnosing')
    launch = d.run([sys.executable,'-m','pbi_linux','open','--diagnostics'], 80, env)
    (out / 'launch.log').write_text(launch.stdout)
    if launch.returncode:
        raise RuntimeError('Launch failed')
    owned = True
    invocation = d.run(['systemctl', '--user', 'show', UNIT, '-p', 'InvocationID', '--value'], 2).stdout.strip()
    group = Path('/sys/fs/cgroup' + d.run(['systemctl', '--user', 'show', UNIT, '-p', 'ControlGroup', '--value'], 2).stdout.strip())
    deadline = time.monotonic() + 90
    report = None
    while time.monotonic() < deadline:
        report = page_with('reportView')
        if report:
            state = page_text(report)
            if state['ready'] == 'complete' and len(state['text']) > 50:
                main_id = report['id']
                main_text = state['text']
                break
        time.sleep(2)
    if not main_id:
        raise RuntimeError('reportView never became ready')
    record({'step': 'ready', 'seconds': round(time.monotonic() - started, 1), 'text': main_text[:300]})

    opening_deadline=time.monotonic()+30
    while time.monotonic()<opening_deadline:
        # First-run coach tips place a backdrop over the Home source tiles.
        # Close their own buttons; never click the main title-bar Close button.
        d.cdp(report,'Runtime.evaluate',{'expression':"document.querySelectorAll('button.close-btn[data-testid=close-btn],button.glyphicon.pbi-glyph-close.glyph-mini').forEach(e=>{if(e.getBoundingClientRect().height>0)e.click()})"})
        result = click_text(report, 'Blank report' if a.entry=='ribbon' else 'Get data from other sources')
        if result.get('result', {}).get('value', {}).get('clicked'):
            break
        time.sleep(2)
    else:
        raise RuntimeError('Get Data entry unavailable')
    if a.entry=='ribbon':
        menu_deadline=time.monotonic()+45
        while time.monotonic()<menu_deadline:
            d.cdp(report,'Runtime.evaluate',{'expression':"document.querySelectorAll('button.close-btn[data-testid=close-btn],button.glyphicon.pbi-glyph-close.glyph-mini').forEach(e=>{if(e.getBoundingClientRect().height>0)e.click()})"})
            result=click_text(report,'Text/CSV')
            if result.get('result',{}).get('value',{}).get('clicked'):
                break
            result=d.cdp(report,'Runtime.evaluate',{'expression':
                "(()=>{const b=document.querySelector('[role=button][aria-label=\"Get data\"] button.splitMenuButton');if(!b||b.disabled)return false;const r=b.getBoundingClientRect(),t=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);if(r.width<=0||r.height<=0||!t||!b.contains(t))return false;const item=document.querySelector('button[name=\"Text/CSV\"][role=menuitem]');if(!item||item.getBoundingClientRect().height<=0)b.click();return true})()",
                'returnByValue':True})
            time.sleep(1)
        else:
            raise RuntimeError('Get Data Text/CSV menu unavailable')
    opened_at = time.monotonic()
    record({'step': 'get-data-clicked','entry':a.entry})
    dialog_deadline = time.monotonic() + 60
    query = None
    while time.monotonic() < dialog_deadline:
        query = page_with('desktop.powerquery.microsoft.com')
        if query:
            break
        time.sleep(1)
    if not query:
        raise RuntimeError('Modern Get Data dialog did not appear')
    if a.entry=='all-sources':
        state = wait_for(lambda: page_text_with(page_with('desktop.powerquery.microsoft.com'), 'Choose data source'),
                         time.monotonic() + 30, 'Get Data home')
        record({'step': 'get-data-dialog', 'text': state['text'][:300]})
        tiles = wait_for(lambda: page_text_with(page_with('desktop.powerquery.microsoft.com'), 'Text/CSV'),
                         time.monotonic() + 90, 'Get Data source tiles')
        record({'step': 'tiles-ready', 'text': tiles['text'][:300]})
        if not ensure_dialog_enabled(time.monotonic() + 60):
            raise RuntimeError('Get Data dialog did not become enabled')
        connect = click_until_state('desktop.powerquery.microsoft.com', 'Text/CSV',
                                    'Connect to data source', time.monotonic() + 90,
                                    'Text/CSV connect form')
    else:
        connect=wait_for(lambda:page_text_with(page_with('desktop.powerquery.microsoft.com'),'Connect to data source'),
                         time.monotonic()+60,'Text/CSV connect form')
        if not ensure_dialog_enabled(time.monotonic()+15):
            raise RuntimeError('Text/CSV dialog did not become enabled')
    record({'step': 'connect-form', 'text': connect['text'][:300]})
    def enter_path():
        result=set_path(page_with('desktop.powerquery.microsoft.com'),csv_path)
        return result.get('result',{}).get('value',{}).get('ok')
    wait_for(enter_path,time.monotonic()+30,'CSV file-path input')
    record({'step': 'path-set', 'path': csv_path})
    preview = click_until_state('desktop.powerquery.microsoft.com', 'Next',
                                'query evaluation is complete', time.monotonic() + 90,
                                'CSV preview evaluation')
    record({'step': 'preview', 'text': preview['text'][:500]})
    try:
        image = d.cdp(page_with('desktop.powerquery.microsoft.com'), 'Page.captureScreenshot', {})
        (out / 'preview.png').write_bytes(base64.b64decode(image['data']))
    except Exception as exc:
        record({'step': 'preview-screenshot-error', 'error': str(exc)})

    load_requested = True
    load_deadline = time.monotonic() + 90
    while time.monotonic() < load_deadline:
        if not any(w['title'] == 'Get Data (Power Query)' for w in window_lines()):
            break
        page = page_with('desktop.powerquery.microsoft.com')
        if page:
            try:
                click_text(page, 'Load')
            except Exception:
                pass
        time.sleep(3)
    else:
        raise RuntimeError('Timeout waiting for Load completion')

    def table_visible():
        for candidate in pages():
            if candidate['type'] == 'page' and ('dataExploreView' in candidate['url'] or 'reportView' in candidate['url']):
                if page_text_with(candidate, table):
                    return True
        return False

    table_seen = wait_for(table_visible, time.monotonic() + 60, 'table in model')
    ports=list((prefix/'drive_c/users').glob('*/AppData/Local/Microsoft/Power BI Desktop/AnalysisServicesWorkspaces/*/Data/msmdsrv.port.txt'))
    raw=max(ports,key=lambda p:p.stat().st_mtime).read_bytes()
    port=raw.decode('utf-16-le' if b'\x00' in raw else 'utf-8-sig').strip('\ufeff\x00 \r\n')
    query="EVALUATE ROW(\"Total\", SUM('"+table.replace("'","''")+"'[Vendas]))"
    evidence=d.run([str(runtime/'bin/wine'),str(a.probes.resolve()/'adomd-probe.exe'),port,query],60,probe_env)
    (out/'dax.log').write_text(evidence.stdout+evidence.stderr)
    loaded=evidence.returncode==0 and any(line.strip()=='COL0: 300' for line in evidence.stdout.splitlines())
    if not loaded:raise RuntimeError('CSV sum 300 not independently confirmed')
    record({'step': 'loaded', 'table': table, 'seconds': round(time.monotonic() - started, 1)})
    if a.save_report:
        visual_values_verified=create_visual()
        record({'step':'visual-values-verified'})
        saved=save_report(a.save_report)
        record({'step':'saved','file':str(a.save_report)})
    for page in pages():
        if page['type'] == 'page' and 'reportView' in page['url']:
            try:
                image = d.cdp(page, 'Page.captureScreenshot', {})
                (out / 'after-load-reportView.png').write_bytes(base64.b64decode(image['data']))
            except Exception as exc:
                record({'step': 'report-screenshot-error', 'error': str(exc)})
    if group.exists():
        peak_memory = int((group / 'memory.peak').read_text().strip())
        (out/'memory-events.txt').write_text((group/'memory.events').read_text())
    traces = sorted((prefix/'drive_c/users').glob(
        '*/AppData/Local/Microsoft/Power BI Desktop/Traces/Performance/*.log'), key=lambda p: p.stat().st_mtime)
    for trace in traces[-4:]:
        if trace.stat().st_mtime >= started_wall:
            (out / ('trace-' + trace.name)).write_bytes(trace.read_bytes())
except BaseException as exc:
    failure = type(exc).__name__ + ': ' + str(exc)
    print('STOP: ' + failure, flush=True)
    if owned:
        for page in pages():
            if page.get('type')!='page':
                continue
            try:
                label='query' if 'powerquery' in page['url'] else 'report' if 'reportView' in page['url'] else None
                if label:
                    (out/('failure-'+label+'.json')).write_text(json.dumps(page_text(page),ensure_ascii=False,indent=2))
                    image=d.cdp(page,'Page.captureScreenshot',{'format':'png'})
                    (out/('failure-'+label+'.png')).write_bytes(base64.b64decode(image['data']))
            except Exception:
                pass
finally:
    if group and group.exists():
        try:
            peak_memory=int((group/'memory.peak').read_text().strip())
            (out/'memory-events.txt').write_text((group/'memory.events').read_text())
        except OSError:
            pass
    if owned:
        try:
            d.run(['systemctl', '--user', 'stop', UNIT], 35)
        except subprocess.TimeoutExpired:
            d.run(['systemctl', '--user', 'kill', '--kill-whom=all', '--signal=KILL', UNIT], 2)
        journal = d.run(['journalctl', '--user', '--no-pager','-u',UNIT,'--since','@'+str(int(started_wall)),'-n','200'], 5)
        (out / 'journal.log').write_text(journal.stdout)
    (out / 'result.json').write_text(json.dumps({
        'failure': failure, 'runtime_sha256':installation['runtime_sha256'], 'entry':a.entry, 'csv_path': csv_path, 'table': table, 'loaded': loaded,
        'table_in_model': bool(locals().get('table_seen')), 'opened_dialog': opened_at is not None,
        'visual_values_verified':visual_values_verified,'visual_certified':False,
        'saved':saved,'saved_report':str(a.save_report) if saved else None,
        'peak_memory_bytes': peak_memory, 'seconds': round(time.monotonic() - started, 1),
    }, indent=2))
    print('Artifacts: ' + str(out), flush=True)
sys.exit(1 if failure else 0)
