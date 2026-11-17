"""The Apple TV app's icon and Top Shelf image (scripts/xbox/tvos-art.py):
plain-colour PNGs made here stand in for the art."""
import pathlib
import plistlib
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/xbox/tvos-art.py'


def png(path, width, height, alpha=255):
    row = b'\0' + bytes((40, 60, 90, alpha)) * width
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)) +
                     chunk(b'IDAT', zlib.compress(row * height, 9)) + chunk(b'IEND', b''))


@unittest.skipUnless(sys.platform == 'darwin' and shutil.which('xcrun') and shutil.which('sips'),
                     'needs Xcode (actool) and sips')
class TvosArtTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.folder.name)
        self.art, self.app = self.root / 'art', self.root / 'App.app'
        self.art.mkdir()
        self.app.mkdir()
        with open(self.app / 'Info.plist', 'wb') as f:
            plistlib.dump({'CFBundleName': 'Test'}, f)

    def tearDown(self):
        self.folder.cleanup()

    def run_art(self):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.art), str(self.root / 'work'), str(self.app),
                               'appletvos'], capture_output=True, text=True)

    def info(self):
        with open(self.app / 'Info.plist', 'rb') as f:
            return plistlib.load(f)

    def add_icon_and_shelf(self):
        png(self.art / 'icon-back.png', 800, 480)
        png(self.art / 'icon-front.png', 800, 480, alpha=0)
        png(self.art / 'topshelf-wide.png', 4640, 1440)

    def test_no_art_leaves_the_app_without_an_icon(self):
        (self.app / 'Assets.car').write_bytes(b'from an earlier build')
        result = self.run_art()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.app / 'Assets.car').exists())
        self.assertEqual(self.info(), {'CFBundleName': 'Test'})

    def test_icon_and_top_shelf_are_compiled_and_named_in_info_plist(self):
        self.add_icon_and_shelf()
        result = self.run_art()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.app / 'Assets.car').stat().st_size > 0)
        info = self.info()
        self.assertEqual(info['CFBundleName'], 'Test')
        self.assertEqual(info['CFBundleIcons']['CFBundlePrimaryIcon'], 'App Icon')
        self.assertEqual(info['TVTopShelfImage']['TVTopShelfPrimaryImageWide'], 'Top Shelf Image Wide')
        layer = self.root / 'work/Assets.xcassets/App Icon & Top Shelf Image.brandassets/App Icon.imagestack'
        self.assertEqual(sorted(p.name for p in layer.glob('*.imagestacklayer')),
                         ['Back.imagestacklayer', 'Front.imagestacklayer'])
        made = subprocess.run(['sips', '-g', 'pixelWidth', str(layer / 'Back.imagestacklayer/Content.imageset/1x.png')],
                              capture_output=True, text=True).stdout
        self.assertIn('pixelWidth: 400', made)

    def test_wrong_size_stops_with_the_file_named(self):
        self.add_icon_and_shelf()
        png(self.art / 'icon-front.png', 400, 240, alpha=0)
        result = self.run_art()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('icon-front.png is 400x240; it must be 800x480', result.stderr)

    def test_one_layer_or_no_top_shelf_is_refused(self):
        png(self.art / 'icon-back.png', 800, 480)
        png(self.art / 'topshelf-wide.png', 4640, 1440)
        self.assertIn('at least two layers', self.run_art().stderr)
        png(self.art / 'icon-front.png', 800, 480, alpha=0)
        (self.art / 'topshelf-wide.png').unlink()
        self.assertIn('topshelf-wide.png', self.run_art().stderr)


if __name__ == '__main__':
    unittest.main()
