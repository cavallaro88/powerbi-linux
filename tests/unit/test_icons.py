# SPDX-License-Identifier: GPL-3.0-or-later
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from pbi_linux import icons, desktop
from pbi_linux.common import Paths


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB', 16,16,8,6,0,0,0))+
            chunk(b'IDAT', zlib.compress((b'\0'+bytes([250,190,0,255])*16)*16))+chunk(b'IEND', b''))


def pe_image(image):
    data=bytearray(0x800);data[:2]=b'MZ';struct.pack_into('<I',data,0x3c,0x80);data[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<H',data,0x86,1);struct.pack_into('<H',data,0x94,240)
    opt=0x98;struct.pack_into('<H',data,opt,0x20b);struct.pack_into('<II',data,opt+128,0x2000,1024)
    struct.pack_into('<IIII',data,opt+240+8,1024,0x2000,1024,0x400)
    def directory(offset, entries):
        struct.pack_into('<HH',data,0x400+offset+12,0,len(entries))
        for i,(key,ptr) in enumerate(entries):struct.pack_into('<II',data,0x400+offset+16+i*8,key,ptr)
    directory(0,[(3,0x80000020),(14,0x80000038)])
    directory(32,[(1,0x80000050)]);directory(56,[(32512,0x80000068)])
    directory(80,[(0,128)]);directory(104,[(0,144)])
    group=struct.pack('<HHHBBBBHHIH',0,1,1,16,16,0,0,1,32,len(image),1)
    struct.pack_into('<IIII',data,0x400+128,0x2000+160,len(image),0,0)
    struct.pack_into('<IIII',data,0x400+144,0x2000+512,len(group),0,0)
    data[0x400+160:0x400+160+len(image)]=image;data[0x600:0x600+len(group)]=group
    return bytes(data)


class IconTests(unittest.TestCase):
    def test_original_png_bytes_are_retained(self):
        image=png();self.assertEqual(icons.application_png(pe_image(image)),image)

    def test_truncated_pe_and_invalid_resource_offsets_are_rejected(self):
        with self.assertRaises(ValueError):icons.application_png(b'MZ')
        data=bytearray(pe_image(png()));struct.pack_into('<I',data,0x400+128,0xffffff00)
        with self.assertRaises(ValueError):icons.application_png(data)

    def test_corrupt_png_is_not_installed(self):
        image=bytearray(png());image[-1]^=1
        with self.assertRaises(ValueError):icons.application_png(pe_image(image))

    def test_local_artwork_cached_and_invalid_manifest_recovers(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ,{
            'XDG_DATA_HOME':tmp+'/data','XDG_CACHE_HOME':tmp+'/cache',
            'XDG_CONFIG_HOME':tmp+'/config','XDG_STATE_HOME':tmp+'/state','XDG_RUNTIME_DIR':tmp+'/run'}):
            paths=Paths();prefix=Path(tmp)/'profile';app=prefix/'drive_c/Program Files/Microsoft Power BI Desktop/bin/PBIDesktop.exe'
            app.parent.mkdir(parents=True);app.write_bytes(pe_image(png()))
            manifest=paths.cache/'desktop-icon.json';manifest.parent.mkdir(parents=True);manifest.write_text('broken json')
            result=icons.install_original(paths,prefix);self.assertEqual(result.read_bytes(),png())
            with patch.object(icons,'application_png',side_effect=AssertionError('Should use verified cache')):
                self.assertEqual(icons.install_original(paths,prefix),result)
            entry=paths.data.parent/'applications'/desktop.DESKTOP_ID;entry.parent.mkdir(parents=True)
            entry.write_text('[Desktop Entry]\nType=Application\nName=Power BI\nExec=preserve-launcher %f\nIcon=powerbi-linux\n')
            desktop.refresh_icon(paths,{'prefix':str(prefix)})
            self.assertIn('Icon='+str(result),entry.read_text());self.assertIn('Exec=preserve-launcher %f',entry.read_text())
            result.unlink();foreign=Path(tmp)/'foreign.png';foreign.write_bytes(b'foreign');result.symlink_to(foreign)
            self.assertIsNone(icons.install_original(paths,prefix));self.assertEqual(foreign.read_bytes(),b'foreign')


if __name__ == '__main__':unittest.main()
