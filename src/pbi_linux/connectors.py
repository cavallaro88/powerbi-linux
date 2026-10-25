# SPDX-License-Identifier: GPL-3.0-or-later
"""Optional original ADO.NET providers, scoped to a managed Desktop prefix."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile
from . import assets
from .common import Error, atomic_json, check_digest, digest, read_json

PROVIDERS = 'drive_c/Program Files/Microsoft Power BI Desktop/bin/ADO.NET Providers'
STATE = 'powerbi-linux-connectors/mysql.json'


def recipe():
    from .provision import resource_root
    return read_json(resource_root() / 'connectors/mysql.lock.json')


def configuration(version):
    if version != '8.0.33':
        raise Error('Unsupported MySQL connector version')
    return ('''<configuration><system.data><DbProviderFactories>
<add name="MySQL Data Provider" invariant="MySql.Data.MySqlClient" description=".NET Framework Data Provider for MySQL" type="MySql.Data.MySqlClient.MySqlClientFactory, MySql.Data, Version=%s.0, Culture=neutral, PublicKeyToken=c5687fc88969c44d" />
</DbProviderFactories></system.data></configuration>
''' % version).encode()


def extract(packages, selected, target):
    """Verify every archive and selected assembly before touching the provider."""
    seen = set()
    for package in selected['packages']:
        archive = packages[package['id']]
        check_digest(archive, package['sha256'])
        member = PurePosixPath(package['assembly'])
        if member.is_absolute() or '..' in member.parts or member.suffix != '.dll':
            raise Error('Unsafe provider assembly path')
        name = member.name
        if name.casefold() in seen:
            raise Error('Duplicate provider assembly')
        seen.add(name.casefold())
        with zipfile.ZipFile(archive) as z:
            if z.namelist().count(str(member)) != 1 or z.getinfo(str(member)).file_size > 32 * 1024**2:
                raise Error('Invalid provider package member')
            data = z.read(str(member))
            if hashlib.sha256(data).hexdigest() != package['assembly_sha256']:
                raise Error('Provider assembly checksum failed')
            (target / name).write_bytes(data)
            notices = target / 'notices' / package['id']
            notices.mkdir(parents=True)
            (notices / 'package.json').write_text(json.dumps(package, indent=2) + '\n')
            # Preserve embedded notices as data; never extract paths from a ZIP.
            for index, notice in enumerate(package.get('notice_files', [])):
                if z.getinfo(notice).file_size > 1024**2:
                    raise Error('Provider notice exceeds size limit')
                (notices / (str(index) + '-' + PurePosixPath(notice).name)).write_bytes(z.read(notice))


def status(prefix):
    prefix = Path(prefix)
    provider = prefix / PROVIDERS
    state = prefix / STATE
    if not state.exists():
        external = any((provider / name).exists() or (provider / name).is_symlink()
                       for name in ('MySql.config', 'MySql'))
        # Vendor MSI packages may use the GAC and global .NET registration
        # instead of Desktop's private provider folder. Do not shadow those.
        configs = list(provider.glob('*.config'))
        configs.extend((prefix / 'drive_c/windows/Microsoft.NET').glob('Framework*/v4.0.30319/Config/machine.config'))
        if not external:
            external = any(f.is_file() and f.stat().st_size < 1024**2 and
                           'MySql.Data.MySqlClient' in f.read_text(errors='replace') for f in configs)
        return {'connector': 'mysql', 'state': 'external' if external else 'not-installed',
                'verified': False, 'detail': 'External provider requires native validation' if external else
                'Optional provider; use pbi-linux connector install mysql --accept-license'}
    saved = read_json(state)
    if saved.get('schema') != 1 or saved.get('connector') != 'mysql' or not saved.get('files'):
        raise Error('Invalid managed MySQL connector manifest')
    for name, sha in saved['files'].items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or '..' in relative.parts or
                not (name == 'MySql.config' or relative.parts[0] == 'MySql')):
            raise Error('Invalid managed MySQL provider path')
        file = provider / name
        if file.is_symlink() or not file.resolve().is_relative_to(provider.resolve()):
            raise Error('MySQL provider escapes its directory')
        check_digest(file, sha)
    return {'connector': 'mysql', 'state': 'installed', 'verified': True,
            'version': saved['version'], 'detail': 'Managed provider files and registration verified; server connectivity is a separate check'}


def install(paths, *, accept_license=False):
    from .provision import active, idle
    if not accept_license:
        raise Error('Read docs/user/connectors.md and the upstream package licenses; supply --accept-license')
    selected = recipe()
    if selected.get('schema') != 1 or selected.get('connector') != 'mysql':
        raise Error('Unsupported connector recipe')
    config = configuration(selected['version'])
    with paths.lock():
        idle(paths)
        prefix = Path(active(paths)['prefix'])
        current = status(prefix)
        if current['state'] == 'installed':
            return current
        if current['state'] == 'external':
            raise Error('An external MySQL provider exists; it will not be overwritten')
        packages = {p['id']: assets.download(p['url'], p['sha256'], paths.cache / 'connectors')
                    for p in selected['packages']}
        provider = prefix / PROVIDERS
        if provider.is_symlink() or not provider.resolve().is_relative_to(prefix.resolve()):
            raise Error('Provider directory escapes the managed prefix')
        provider.mkdir(parents=True, exist_ok=True)
        committed = []
        try:
            with tempfile.TemporaryDirectory(prefix='.mysql-', dir=provider) as temporary:
                stage = Path(temporary)
                (stage / 'MySql').mkdir()
                extract(packages, selected, stage / 'MySql')
                (stage / 'MySql.config').write_bytes(config)
                files = {str(f.relative_to(stage)): digest(f) for f in stage.rglob('*') if f.is_file()}
                for name in ('MySql', 'MySql.config'):
                    os.rename(stage / name, provider / name)
                    committed.append(provider / name)
                atomic_json(prefix / STATE, {'schema': 1, 'connector': 'mysql',
                                             'version': selected['version'], 'files': files})
        except BaseException:
            for file in reversed(committed):
                if file.is_dir():
                    shutil.rmtree(file)
                else:
                    file.unlink(missing_ok=True)
            raise
        return status(prefix)
