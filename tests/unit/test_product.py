# SPDX-License-Identifier: GPL-3.0-or-later
import io
import json
import os
from pathlib import Path
import socket
import shutil
import shlex
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from pbi_linux import assets, common, launch, provision, pe_cache, desktop, webview


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {name:str(self.root/name) for name in
                    ('XDG_DATA_HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_RUNTIME_DIR')})
        self.env.start()
        self.paths = common.Paths()
        self.paths.create()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_xdg_isolation_and_private_metadata(self):
        common.atomic_json(self.paths.active, {'sample':'value'})
        self.assertTrue(self.paths.active.is_relative_to(self.root))
        self.assertEqual(self.paths.active.stat().st_mode & 0o777, 0o600)
        self.assertEqual(common.read_json(self.paths.active), {'sample':'value'})

    def test_wine_installer_reboot_status_requires_explicit_opt_in(self):
        result=subprocess.CompletedProcess(['wine','installer.exe'],194,stdout='',stderr='')
        with patch.object(common.subprocess,'run',return_value=result):
            with self.assertRaises(common.Error):common.run(['ordinary-command'])
            common.run(['wine','installer.exe'],success_codes=(0,194))

    def test_lock_serializes_open_and_maintenance(self):
        with self.paths.lock():
            with self.assertRaises(common.Error):
                with self.paths.lock():
                    self.fail('Acquired an already held maintenance lock')

    def test_source_export_excludes_model_cache_credentials_and_binaries(self):
        project=self.root/'standalone'
        actual=Path(__file__).resolve().parents[2]
        for name in ('src','runtime','tests','packaging','tools','docs','.github','LICENSES'):
            (project/name).mkdir(parents=True)
        for name in ('LICENSE','README.md','CONTRIBUTING.md','SECURITY.md','CODE_OF_CONDUCT.md','CHANGELOG.md','.gitignore'):
            (project/name).write_text('public')
        shutil.copy2(actual/'tools/export-source.py',project/'tools/export-source.py')
        fixture=project/'tests/synthetic'
        (fixture/'.pbi').mkdir(parents=True)
        for name in ('.pbi/cache.abf','.env','.env.local','customer.pbix','Customer.PBIX','key.snk','built.dll'):
            (fixture/name).write_text('private test sentinel')
        (fixture/'definition.pbir').write_text('public synthetic definition')
        export=self.root/'public-export'
        subprocess.run([sys.executable,project/'tools/export-source.py',export],check=True,capture_output=True)
        files=[p for p in export.rglob('*') if p.is_file()]
        self.assertFalse(any('private test sentinel' in p.read_text() for p in files))
        self.assertTrue((export/'tests/synthetic/definition.pbir').is_file())
        # A destination inside an exported directory would recursively copy
        # itself, potentially filling the user's disk before packaging.
        nested=project/'tests/nested-export'
        rejected=subprocess.run([sys.executable,project/'tools/export-source.py',nested],capture_output=True)
        self.assertNotEqual(rejected.returncode,0)
        self.assertFalse(nested.exists())

    def test_paths_are_passed_as_single_arguments(self):
        source = self.root/'relatório $(touch nope) ; spaced.PBIX'
        source.touch()
        self.assertEqual(launch.file_argument(str(source)), str(source))
        with self.assertRaises(common.Error):
            launch.file_argument(str(self.root/'missing.pbip'))
        with self.assertRaises(common.Error):
            launch.file_argument(str(self.root/'not-a-project.exe'))

    def test_all_supported_file_extensions(self):
        for extension in ('.pbix','.pbip','.pbir'):
            file = self.root/('file'+extension)
            file.touch()
            self.assertEqual(launch.file_argument(str(file)),str(file))

    def tar_entry(self, name, *, link=None):
        archive = self.root/'runtime.tar'
        with tarfile.open(archive, 'w') as tar:
            member = tarfile.TarInfo(name)
            if link:
                member.type = tarfile.SYMTYPE
                member.linkname = link
                tar.addfile(member)
            else:
                member.size = 1
                tar.addfile(member, io.BytesIO(b'x'))
        return archive

    def test_archive_rejects_traversal(self):
        for index, name in enumerate(('../escape','/tmp/escape')):
            archive = self.tar_entry(name)
            with self.assertRaises(common.Error):
                assets.extract_runtime(archive,self.root/('extract'+str(index)))
        self.assertFalse((self.root.parent/'escape').exists())

    def test_archive_rejects_symlink_escape(self):
        archive = self.tar_entry('link', link='../../outside')
        with self.assertRaises(common.Error):
            assets.extract_runtime(archive,self.root/'extracted')

    def runtime(self):
        runtime=self.paths.data/'runtimes/test'
        files={}
        for name in ('bin/wine','bin/wineserver','bin/winepath','helpers/PowerBICompositionManager.dll'):
            file=runtime/name
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(b'test')
            files[name]=common.digest(file)
        common.atomic_json(runtime/'runtime.json',{'schema':1,'arch':'x86_64','files':files})
        return runtime

    def test_runtime_verification_detects_tampering(self):
        runtime=self.runtime()
        assets.verify_runtime(runtime)
        (runtime/'bin/wine').write_text('tampered')
        with self.assertRaises(common.Error):
            assets.verify_runtime(runtime)

    def test_failed_update_does_not_activate_or_replace_previous(self):
        runtime=self.runtime()
        prefix=self.paths.data/'profiles/current'
        prefix.mkdir(parents=True)
        initial={'schema':1,'prefix':str(prefix),'runtime':str(runtime),'patches':{},'runtime_sha256':'a'*64}
        common.atomic_json(self.paths.active,initial)
        class Args:
            command='update'
            runtime='/missing'
            runtime_sha256='f'*64
        with patch.object(provision,'idle'), patch.object(provision,'install_runtime',side_effect=common.Error('bad runtime')):
            with self.assertRaises(common.Error):
                provision.maintain(self.paths,Args())
        self.assertEqual(common.read_json(self.paths.active),initial)
        self.assertFalse(self.paths.previous.exists())

    def test_failed_snapshot_removes_only_its_partial_copy(self):
        source=self.root/'source-profile'
        source.mkdir(); (source/'document.txt').write_text('preserve')
        target=self.root/'pending-snapshot'
        def partial(command, **kwargs):
            (target/'incomplete.txt').write_text('partial copy')
            raise common.Error('Disk full')
        with patch.object(provision,'run',side_effect=partial):
            with self.assertRaises(common.Error):provision.snapshot(source,target)
        self.assertFalse(target.exists())
        self.assertEqual((source/'document.txt').read_text(),'preserve')

    def test_interrupted_setup_resumes_completed_stages_before_activation(self):
        source=self.root/'installer.exe'
        source.write_bytes(b'synthetic installer')
        runtime=self.runtime()
        args=SimpleNamespace(accept_license=True,installer=str(source),runtime='/unused',
            runtime_sha256='a'*64,webview_runtime=str(source),
            dotnet_installer=str(source),dotnet40_installer=str(source),make_default=False)
        commands=[]
        interrupted=True
        def stage(command, **kwargs):
            if 'env' in kwargs:
                self.assertIn('winemenubuilder.exe=d',kwargs['env']['WINEDLLOVERRIDES'])
            commands.append([str(x) for x in command])
            if 'wineboot.exe' in commands[-1]:
                self.assertTrue((Path(kwargs['env']['WINEPREFIX'])/'drive_c/powerbi-linux-inputs').is_dir())
            if interrupted and commands[-1][1].endswith('/dotnet40.exe'):
                raise common.Error('Simulated interrupted installer')
        edge=self.root/'154.0.4258.53/msedge.dll'
        with patch.object(provision,'idle'), patch.object(provision,'check_digest'), \
             patch.object(provision,'webview_config',return_value=provision.webview_config()), \
             patch.object(assets,'download',return_value=source), \
             patch.object(provision,'install_runtime',return_value=runtime), \
             patch.object(provision,'run',side_effect=stage), patch.object(provision,'stop_server'), \
             patch.object(provision,'configure',return_value={}), \
             patch.object(provision,'verified_webview',return_value=edge), patch.object(pe_cache,'prepare'), \
             patch.object(desktop,'integrate') as integration:
            with self.assertRaises(common.Error):
                provision.setup(self.paths,args)
            self.assertFalse(self.paths.active.exists())
            self.assertFalse(self.paths.previous.exists())
            integration.assert_not_called()
            interrupted=False
            provision.setup(self.paths,args)
            integration.assert_called_once()
        self.assertEqual(sum('wineboot.exe' in c for c in commands),1)
        self.assertTrue(self.paths.active.exists())

    def test_uninstall_clears_only_our_empty_previous_association(self):
        # GIO can auto-select a newly registered sole handler before an explicit
        # default was saved. Uninstall must also clear our token in that case.
        common.atomic_json(self.paths.config/'desktop.json', {'defaults':{}})
        file=self.paths.config.parent/'mimeapps.list'
        file.write_text('[Default Applications]\n'+desktop.MIMES[0]+'='+desktop.DESKTOP_ID+';\n'
                        'application/pdf=reader.desktop;\n[Added Associations]\ntext/plain=editor.desktop;\n')
        response=SimpleNamespace(stdout=desktop.DESKTOP_ID+'\n',returncode=0)
        with patch.object(desktop.shutil,'which',return_value='/usr/bin/tool'), \
             patch.object(desktop.subprocess,'run',return_value=response):
            desktop.remove(self.paths)
        content=file.read_text()
        self.assertNotIn(desktop.MIMES[0],content)
        self.assertIn('reader.desktop;',content)
        self.assertIn('editor.desktop;',content)

    def test_rollback_swaps_snapshots(self):
        runtime=self.runtime()
        first=self.paths.data/'profiles/first'
        second=self.paths.data/'profiles/second'
        first.mkdir(parents=True)
        second.mkdir(parents=True)
        one={'prefix':str(first),'runtime':str(runtime),'patches':{},'runtime_sha256':'a'*64}
        two={**one,'prefix':str(second)}
        common.atomic_json(self.paths.active,two)
        common.atomic_json(self.paths.previous,one)
        with patch.object(provision,'idle'):
            provision.rollback(self.paths)
        self.assertEqual(common.read_json(self.paths.active),one)
        self.assertEqual(common.read_json(self.paths.previous),two)

    def test_legacy_wine_cleanup_preserves_foreign_prefixes_and_shared_mime(self):
        apps=self.paths.data.parent/'applications';apps.mkdir(parents=True)
        mimes=self.paths.data.parent/'mime/packages';mimes.mkdir(parents=True)
        owned=self.paths.data/'profiles'/'snapshot-retired'
        foreign=self.root/'other-wine-prefix'
        def entry(name,prefix,mime):
            file=apps/name
            file.write_text('[Desktop Entry]\nType=Application\nName=Fixture\nMimeType='+mime+';\nExec=env '+shlex.quote('WINEPREFIX='+str(prefix))+' wine start %f\n')
            return file
        removed=entry('wine-extension-pbix.desktop',owned,'application/x-wine-extension-pbix')
        preserved=entry('wine-extension-reg.desktop',foreign,'application/x-wine-extension-reg')
        shared=entry('wine-extension-xaml.desktop',owned,'application/x-wine-extension-xaml')
        reader=entry('other-reader.desktop',foreign,'application/x-wine-extension-xaml')
        for name in ('pbix','reg','xaml'):(mimes/('x-wine-extension-'+name+'.xml')).write_text('MIME fixture')
        with patch.dict(os.environ,{'XDG_DATA_DIRS':str(self.root/'system')}):
            desktop.remove_legacy_wine_entries(self.paths)
        self.assertFalse(removed.exists());self.assertFalse(shared.exists())
        self.assertTrue(preserved.exists());self.assertTrue(reader.exists())
        self.assertFalse((mimes/'x-wine-extension-pbix.xml').exists())
        self.assertTrue((mimes/'x-wine-extension-reg.xml').exists())
        self.assertTrue((mimes/'x-wine-extension-xaml.xml').exists())

    def test_user_uninstall_masks_the_rpm_entry_and_repair_restores_it(self):
        system=self.root/'system-share'
        entry=system/'applications'/desktop.DESKTOP_ID
        entry.parent.mkdir(parents=True)
        entry.write_text('[Desktop Entry]\nName=System entry sentinel\nType=Application\nExec=true\n')
        original=entry.read_bytes()
        with patch.dict(os.environ,{'XDG_DATA_DIRS':str(system)}), patch.object(desktop.shutil,'which',return_value=None):
            desktop.remove(self.paths)
            user=self.paths.data.parent/'applications'/desktop.DESKTOP_ID
            self.assertIn('Hidden = true',user.read_text())
            self.assertEqual(entry.read_bytes(),original)
            desktop.integrate(self.paths)
            self.assertNotIn('Hidden',user.read_text())
            self.assertEqual(entry.read_bytes(),original)

    def test_invalid_rollback_preserves_active(self):
        common.atomic_json(self.paths.active,{'sentinel':True})
        common.atomic_json(self.paths.previous,{'prefix':'/outside','runtime':'/outside','patches':{}})
        with patch.object(provision,'idle'):
            with self.assertRaises(common.Error):
                provision.rollback(self.paths)
        self.assertEqual(common.read_json(self.paths.active),{'sentinel':True})

    def test_cache_identity_changes_with_source_identity(self):
        file=self.root/'edge.dll'
        file.write_text('source')
        before=pe_cache.identity(file.stat(),123,456)
        replacement=self.root/'new.dll'
        replacement.write_text('source')
        replacement.replace(file)
        self.assertNotEqual(pe_cache.identity(file.stat(),123,456),before)

    def test_release_env_disables_diagnostic_inheritance(self):
        runtime=self.runtime()
        prefix=self.paths.data/'profiles/test'
        prefix.mkdir(parents=True)
        install={'prefix':str(prefix),'runtime':str(runtime),'patches':{}}
        with patch.dict(os.environ, {'PBI_UI_DIAGNOSTICS':'1','PBI_WAYLAND_CAPTURE_DIR':'/tmp/secret',
                 'WINELOADER':'/old/wine','WINESERVER':'/old/wineserver','WINEARCH':'win32',
                 'WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS':'--remote-debugging-port=9229'}), \
             patch.object(launch,'verified_webview',return_value=prefix/'edge.dll'), patch.object(pe_cache,'valid',return_value=False):
            env=launch.environment(self.paths,install)
            setup_env=common.wine_env(prefix)
        self.assertNotIn('PBI_UI_DIAGNOSTICS',env)
        self.assertNotIn('PBI_WAYLAND_CAPTURE_DIR',env)
        self.assertNotIn('remote-debugging',env['WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS'])
        self.assertEqual(env['APPDOMAIN_MANAGER_TYPE'],'CompositionManager')
        self.assertIn('winemenubuilder.exe=d',env['WINEDLLOVERRIDES'])
        self.assertIn('winemenubuilder.exe=d',setup_env['WINEDLLOVERRIDES'])
        self.assertNotIn('DISPLAY',env)
        for key in ('WINELOADER','WINESERVER','WINEARCH','PBI_UI_DIAGNOSTICS','PBI_WAYLAND_CAPTURE_DIR'):
            self.assertNotIn(key,env)
            self.assertNotIn(key,setup_env)

    def test_unvalidated_webview_is_rejected_before_launch(self):
        prefix=self.paths.data/'profiles/test'
        source=prefix/'drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/155.0.0.0/msedge.dll'
        source.parent.mkdir(parents=True)
        source.write_bytes(b'unknown updated version')
        with self.assertRaisesRegex(common.Error,'Fixed WebView2 runtime is not provisioned'):
            provision.verified_webview(prefix)

    def fixed_config(self):
        dll=self.root/'dll';dll.write_bytes(b'synthetic browser DLL')
        exe=self.root/'exe';exe.write_bytes(b'synthetic browser EXE')
        return {'distribution':'fixed','runtime_version':'154.0.4258.62',
                'runtime_dll_sha256':common.digest(dll),'runtime_exe_sha256':common.digest(exe),
                'cab_root':'Microsoft.FixedRuntime','sha256':common.digest(dll)},dll,exe

    def test_fixed_webview_is_independent_of_evergreen_updates(self):
        config,dll,exe=self.fixed_config()
        prefix=self.paths.data/'profiles/fixed'
        fixed=webview.folder(prefix,config);fixed.mkdir(parents=True)
        shutil.copy2(dll,fixed/'msedge.dll');shutil.copy2(exe,fixed/'msedgewebview2.exe')
        evergreen=prefix/'drive_c/Program Files (x86)/Microsoft/EdgeWebView/Application/155.0.0.0'
        evergreen.mkdir(parents=True);(evergreen/'msedge.dll').write_bytes(b'unknown automatic update')
        with patch.object(provision,'webview_config',return_value=config):
            self.assertEqual(provision.verified_webview(prefix),fixed/'msedge.dll')
            (fixed/'msedge.dll').write_bytes(b'tampered')
            with self.assertRaises(common.Error):provision.verified_webview(prefix)

    def test_failed_fixed_webview_extraction_preserves_the_profile(self):
        config,dll,exe=self.fixed_config()
        prefix=self.paths.data/'profiles/fixed'
        target=webview.folder(prefix,config);target.mkdir(parents=True)
        (target/'msedge.dll').write_bytes(b'old transaction copy')
        with patch.object(webview.shutil,'which',return_value='/usr/bin/cabextract'), \
             patch.object(webview,'run',side_effect=common.Error('interrupted extraction')):
            with self.assertRaises(common.Error):webview.install(prefix,dll,config,self.root/'extract.log')
        self.assertEqual((target/'msedge.dll').read_bytes(),b'old transaction copy')
        self.assertFalse(list(target.parent.glob('.extract-*')))

    def test_broker_starts_in_service_with_explicit_module_path(self):
        runtime=self.runtime()
        prefix=self.paths.data/'profiles/test'
        prefix.mkdir(parents=True)
        common.atomic_json(self.paths.active,{'prefix':str(prefix),'runtime':str(runtime),'patches':{}})
        display=self.root/'wayland-test'
        with socket.socket(socket.AF_UNIX) as sock:
            sock.bind(str(display))
            commands=[]
            def run(cmd, **kwargs):
                commands.append(cmd)
                self.paths.socket.touch()
                return ''
            read_text = Path.read_text
            def platform_text(file, *args, **kwargs):
                return 'ID=fedora\n' if file == Path('/etc/os-release') else read_text(file, *args, **kwargs)
            with patch.dict(os.environ,{'WAYLAND_DISPLAY':str(display)}), patch.object(launch.shutil,'which',return_value='/usr/bin/tool'), \
                 patch.object(launch,'run',side_effect=run), patch.object(launch,'request',return_value={'ok':True}), \
                 patch.object(Path,'read_text',platform_text):
                launch.open_file(self.paths,None)
        cmd=commands[0]
        self.assertEqual(cmd[-3:],['-m','pbi_linux','_session'])
        self.assertTrue(any(x.startswith('--setenv=PYTHONPATH=') for x in cmd))
        self.assertIn('MemoryMax=infinity',cmd)
        self.assertIn('MemorySwapMax=infinity',cmd)
        self.assertFalse(any(x.startswith('CPUQuota=') for x in cmd))
        self.assertIn('KillMode=mixed',cmd)

if __name__=='__main__':
    unittest.main()
