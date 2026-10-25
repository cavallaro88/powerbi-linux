# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve user setup choices to the existing verified provisioning inputs."""
from argparse import Namespace
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from . import assets, provision, recipes, platforms
from .common import Error, check_digest, read_json, digest

DOWNLOAD_PAGE = 'https://www.microsoft.com/pt-br/download/details.aspx?id=58494'
GUIDE = 'https://github.com/cavallaro88/powerbi-linux/blob/main/docs/user/install.md'


def release(root):
    manifest = read_json(root / 'packaging/setup.json')
    lock = read_json(root / 'runtime/sources.lock.json')
    if manifest.get('schema') != 1 or manifest.get('powerbi', {}).get('version') != lock['powerbi']['version']:
        raise Error('Setup metadata and Power BI recipe differ; install matching project packages')
    if manifest['powerbi'].get('sha256') != lock['powerbi']['sha256']:
        raise Error('Setup metadata and Power BI checksum differ')
    return manifest, lock


def validate_download(component, *, microsoft=False):
    if not isinstance(component, dict):
        raise Error('No validated download is configured for this component')
    url = component.get('url', '')
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
        raise Error('Setup downloads require an HTTPS URL without credentials')
    if microsoft and parsed.hostname != 'download.microsoft.com':
        raise Error('The Power BI installer must come from download.microsoft.com')
    if not re.fullmatch('[a-f0-9]{64}', component.get('sha256', '')):
        raise Error('Setup download has no valid SHA-256')


def validate_runtime_download(component):
    validate_download(component)
    if not component.get('version'):
        raise Error('The runtime download must identify its version')
    for name in ('url', 'source_url', 'evidence_url'):
        parsed = urlsplit(component.get(name, ''))
        if (parsed.scheme != 'https' or parsed.hostname != 'github.com' or
                not parsed.path.startswith('/cavallaro88/powerbi-linux/releases/download/') or
                parsed.username or parsed.password):
            raise Error('Runtime binary, corresponding source and evidence must identify fixed project release assets')


def prepare(paths, args):
    """No Wine processes or active-profile changes occur in this front end."""
    args = Namespace(**vars(args))
    if paths.active.exists():
        raise Error('Power BI is already installed. Use pbi-linux open, repair or update; setup does not upgrade Desktop')
    if bool(args.runtime) != bool(args.runtime_sha256):
        raise Error('Supply --runtime and --runtime-sha256 together, or omit both for the release download')
    manifest, lock = release(provision.resource_root())
    if args.installer:
        try:
            lock['powerbi'] = recipes.installer(digest(Path(args.installer).expanduser()), lock['powerbi'])
        except Error as exc:
            raise Error('Unsupported Power BI installer: expected version ' + lock['powerbi']['version'] +
                        ' or another exact guarded recipe. The current Microsoft download may be newer. ' +
                        'Download page: ' + DOWNLOAD_PAGE + '. Guide: ' + GUIDE) from exc
    args.powerbi_version = lock['powerbi']['version']
    automatic = not args.runtime or not args.installer
    print('Power BI Linux — beta setup', flush=True)
    print('Targets: ' + platforms.TARGETS + '; Vulkan graphics and a systemd user session required.', flush=True)
    print('Power BI Desktop ' + lock['powerbi']['version'] + '; WebView2 ' + lock['webview2']['runtime_version'], flush=True)
    if automatic:
        if not args.runtime and manifest.get('status') != 'ready':
            raise Error('Automatic setup is not available in this release: ' +
                        manifest.get('reason', 'validated release downloads are pending') +
                        '. Local setup requires --runtime and --runtime-sha256; --installer is optional. Guide: ' + GUIDE)
        if not args.runtime:
            validate_runtime_download(manifest.get('runtime'))
        if not args.installer:
            validate_download(manifest.get('powerbi'), microsoft=True)
    # Reject incorrect local files before network activity or user-profile changes.
    if args.runtime:
        check_digest(Path(args.runtime).expanduser(), args.runtime_sha256)
    if args.installer:
        try:
            check_digest(Path(args.installer).expanduser(), lock['powerbi']['sha256'])
        except Error as exc:
            raise Error('Unsupported Power BI installer: expected version ' + lock['powerbi']['version'] +
                        ' with the release SHA-256. The current Microsoft download may be newer. ' +
                        'Download page: ' + DOWNLOAD_PAGE + '. Guide: ' + GUIDE) from exc
    for option, name in (('webview_runtime', 'webview2'), ('dotnet_installer', 'dotnet48'),
                         ('dotnet40_installer', 'dotnet40')):
        value = getattr(args, option)
        if value:
            check_digest(Path(value).expanduser(), lock[name]['sha256'])
            setattr(args, option, str(Path(value).expanduser().resolve()))
    print('Setup prepares a dedicated installation (about 9 GiB, plus runtime, downloads and reports).', flush=True)
    print('Allow several minutes for setup, plus download time; slower machines may take longer.', flush=True)
    print('The .NET and Power BI installers can run for minutes without terminal output. '
          'Silence does not by itself mean setup has frozen; wait for completion or an explicit error.', flush=True)
    if automatic:
        print('Downloads: ' + ', '.join(name for name, needed in (
            ('project Wine/DXVK runtime from the pinned release', not args.runtime),
            ('Power BI installer from Microsoft', not args.installer)) if needed), flush=True)
    print('Additional prerequisites are downloaded from the pinned sources as needed: WebView2, .NET, Wine Gecko and fonts.', flush=True)
    if not args.accept_license:
        print('Read the Microsoft installer terms and project licensing notes before continuing:\n' +
              'https://github.com/cavallaro88/powerbi-linux/blob/main/docs/reference/legal.md', flush=True)
        if not sys.stdin.isatty():
            raise Error('Non-interactive setup requires --accept-license after reviewing the terms')
        try:
            answer = input('Accept the terms and local compatibility modifications? [y/N] ')
        except (EOFError, KeyboardInterrupt) as exc:
            raise Error('Setup canceled; no installation was activated') from exc
        if answer.strip().lower() not in ('y', 'yes'):
            raise Error('Setup canceled; the terms were not accepted')
        args.accept_license = True
    if not args.runtime:
        item = manifest['runtime']
        print('Downloading project runtime ' + item['version'] + '...', flush=True)
        args.runtime = str(assets.download(item['url'], item['sha256'], paths.cache / 'downloads'))
        args.runtime_sha256 = item['sha256']
    else:
        args.runtime = str(Path(args.runtime).expanduser().resolve())
    if not args.installer:
        item = manifest['powerbi']
        print('Downloading Power BI Desktop ' + item['version'] + ' from Microsoft...', flush=True)
        args.installer = str(assets.download(item['url'], item['sha256'], paths.cache / 'downloads'))
    else:
        args.installer = str(Path(args.installer).expanduser().resolve())
    return args
