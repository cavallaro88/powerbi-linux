# SPDX-License-Identifier: GPL-3.0-or-later
"""Exact Desktop installer identities; runtime and app versions are independent."""
from .common import Error

POWERBI = {
    '2.158.1177.0': {
        'version': '2.158.1177.0',
        'sha256': '4924187834d34605c3046f01b876fba6a2cf36f864c36d16fd52c3f17a21009c',
    },
    '2.159.883.0': {
        'version': '2.159.883.0',
        'sha256': '5412131d1f5d535e42358cb6d496703c3c0cdf9267779ac9220171f58ce20cdd',
        'url': 'https://download.microsoft.com/download/8/8/0/880bca75-79dd-466a-927d-1abf1f5454b0/PBIDesktopSetup_x64.exe',
    },
}


def powerbi(version):
    if version not in POWERBI:
        raise Error('The installed Power BI recipe differs from supported project recipes; use the matching project release')
    return dict(POWERBI[version])


def installer(checksum, default):
    if checksum == default['sha256']:
        return dict(default)
    for entry in POWERBI.values():
        if entry['sha256'] == checksum:
            return dict(entry)
    raise Error('Unsupported Power BI installer; no matching guarded recipe')
