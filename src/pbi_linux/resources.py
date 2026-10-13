# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional resource policy; browsers manage their own heap by default."""
import re
from .common import Error, read_json

BASE_BROWSER_FLAGS = '--use-gl=angle --use-angle=d3d11 --disable-direct-composition'
DEFAULTS = {
    'resource_schema': 2, 'memory_profile': 'unlimited',
    'memory_max': 'infinity', 'swap_max': 'infinity', 'cpu_quota': 'infinity',
    'webview_heap_mb': 'auto', 'renderer_process_limit': 'auto',
    'browser_mode': 'standard',
}


def memory_limit(value, *, swap=False):
    if isinstance(value, str):
        if value.lower() in ('unlimited', 'infinity'):
            return 'infinity'
        value = value.upper()
        if re.fullmatch(r'[1-9][0-9]*[MG]', value) or (swap and value == '0'):
            return value
    raise Error('Use unlimited or a positive M/G quantity' + ('; swap also accepts 0' if swap else ''))


def heap_limit(value):
    if value == 'auto':
        return 'auto'
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,4}', value):
        value = int(value)
    if type(value) is int and 128 <= value <= 8192:
        return value
    raise Error('WebView heap must be auto or an integer from 128 to 8192 MiB')


def renderer_limit(value):
    if value == 'auto':
        return 'auto'
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,3}', value):
        value = int(value)
    if type(value) is int and 1 <= value <= 128:
        return value
    raise Error('Renderer process limit must be auto or an integer from 1 to 128')


def cpu_limit(value):
    if isinstance(value, str):
        if value.lower() in ('unlimited', 'infinity'):
            return 'infinity'
        if re.fullmatch(r'[0-9]+(?:\.[0-9]+)?%', value) and float(value[:-1]) > 0:
            return value
    raise Error('CPU quota must be unlimited or a positive percentage, e.g. 200%')


def validate(config):
    value = dict(config)
    value['memory_max'] = memory_limit(value['memory_max'])
    value['swap_max'] = memory_limit(value['swap_max'], swap=True)
    value['cpu_quota'] = cpu_limit(value['cpu_quota'])
    value['webview_heap_mb'] = heap_limit(value['webview_heap_mb'])
    value['renderer_process_limit'] = renderer_limit(value['renderer_process_limit'])
    if value['browser_mode'] not in ('standard', 'economy'):
        raise Error('Browser mode must be standard or economy')
    return value


def load(paths):
    saved = read_json(paths.settings) if paths.settings.exists() else {}
    if not isinstance(saved, dict):
        raise Error('Settings must contain a JSON object')
    saved = dict(saved)
    # Release 1 wrote these bundled limits without an explicit resource opt-in.
    # Only migrate an exact legacy preset; preserve custom values and every
    # explicit schema-2 selection, including a newly selected normal/large.
    if 'resource_schema' not in saved:
        profile = saved.get('memory_profile', 'normal')
        pair = ('10G', '4G') if profile == 'large' else ('6G', '2G')
        if (profile in ('normal', 'large')
                and saved.get('memory_max', pair[0]) == pair[0]
                and saved.get('swap_max', pair[1]) == pair[1]
                and saved.get('webview_heap_mb', 512) == 512
                and not any(k in saved for k in ('cpu_quota', 'browser_mode', 'renderer_process_limit'))):
            for key in ('memory_profile', 'memory_max', 'swap_max', 'webview_heap_mb'):
                saved.pop(key, None)
    return validate({**DEFAULTS, **saved, 'resource_schema': 2})


def preset(name):
    config = dict(DEFAULTS)
    if name in ('normal', 'large'):
        config.update(memory_profile=name, memory_max='10G' if name == 'large' else '6G',
                      swap_max='4G' if name == 'large' else '2G', webview_heap_mb=512,
                      browser_mode='economy', renderer_process_limit=2)
    return config


def browser_flags(config):
    config = validate(config)
    flags = [BASE_BROWSER_FLAGS]
    if config['webview_heap_mb'] != 'auto':
        flags.append('--js-flags=--max_old_space_size=' + str(config['webview_heap_mb']))
    if config['renderer_process_limit'] != 'auto':
        flags.append('--renderer-process-limit=' + str(config['renderer_process_limit']))
    if config['browser_mode'] == 'economy':
        flags.extend(('--process-per-site', '--enable-low-end-device-mode',
                      '--disable-features=SpareRendererForSitePerProcess'))
    return ' '.join(flags)


def service_properties(config):
    config = validate(config)
    result = ['MemoryMax=' + config['memory_max'], 'MemorySwapMax=' + config['swap_max']]
    if config['cpu_quota'] != 'infinity':
        result.append('CPUQuota=' + config['cpu_quota'])
    return result
