#!/usr/bin/env python3
"""The Apple TV app's icon and Top Shelf image, from the PNGs in
port/xbox/tvos-art (its README lists them).

Writes an asset catalog (Assets.xcassets) in the build folder, with the 1x
sizes made from the 2x art (sips), compiles it with Xcode's actool into the
app (Assets.car) and adds the keys actool asks for to the app's Info.plist.
When the folder has no art, the app is left without an icon, as before.

  tvos-art.py ART_DIR WORK_DIR APP_DIR SDK
"""
import json
import pathlib
import plistlib
import shutil
import subprocess
import sys

# the art's sizes in pixels (2x, except the App Store icon's, which is 1x only)
ICON = (800, 480)
STORE = (1280, 768)
WIDE = (4640, 1440)
SHELF = (3840, 1440)
LAYERS = ('front', 'middle', 'back')   # the order tvOS stacks them: front first
INFO = {'author': 'xcode', 'version': 1}
BRAND = 'App Icon & Top Shelf Image'


def fail(message):
    sys.exit('tvos-art: ' + message)


def size_of(path):
    out = subprocess.run(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', str(path)],
                         capture_output=True, text=True, check=True).stdout
    values = dict(line.split(':') for line in out.splitlines()[1:] if ':' in line)
    return int(values['  pixelWidth'].strip()), int(values['  pixelHeight'].strip())


def check(path, size):
    actual = size_of(path)
    if actual != size:
        fail('%s is %dx%d; it must be %dx%d' % (path.name, actual[0], actual[1], size[0], size[1]))


def scaled(source, target, size):
    subprocess.run(['sips', '-z', str(size[1]), str(size[0]), str(source), '--out', str(target)],
                   capture_output=True, check=True)


def write(folder, contents):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'Contents.json').write_text(json.dumps(dict(contents, info=INFO), indent=2) + '\n')


def image_set(folder, source, size, retina=True):
    """An image set: the art at 2x and a 1x made from it, or 1x only."""
    if retina:
        write(folder, {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': '1x.png'},
                                  {'idiom': 'tv', 'scale': '2x', 'filename': '2x.png'}]})
        shutil.copyfile(source, folder / '2x.png')
        scaled(source, folder / '1x.png', (size[0] // 2, size[1] // 2))
    else:
        write(folder, {'images': [{'idiom': 'tv', 'scale': '1x', 'filename': '1x.png'}]})
        shutil.copyfile(source, folder / '1x.png')


def image_stack(folder, layers, size, retina=True):
    """A layered icon: one image set per layer, front first."""
    write(folder, {'layers': [{'filename': name.capitalize() + '.imagestacklayer'} for name, _ in layers]})
    for name, source in layers:
        layer = folder / (name.capitalize() + '.imagestacklayer')
        write(layer, {})
        image_set(layer / 'Content.imageset', source, size, retina)


def main():
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    art, work, app, sdk = (pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]),
                           pathlib.Path(sys.argv[3]), sys.argv[4])
    (app / 'Assets.car').unlink(missing_ok=True)
    icon = [(name, art / ('icon-%s.png' % name)) for name in LAYERS if (art / ('icon-%s.png' % name)).exists()]
    if not icon:
        print('tvos-art: no art in %s; the app has no icon' % art)
        return
    if not (art / 'icon-back.png').exists():
        fail('icon-back.png is needed: the icon\'s bottom layer, opaque')
    if len(icon) < 2:
        fail('the icon needs at least two layers: icon-back.png and icon-front.png (icon-middle.png is optional)')
    for _, path in icon:
        check(path, ICON)
    store = [(name, art / ('appstore-%s.png' % name)) for name, _ in icon]
    if all(path.exists() for _, path in store):
        for _, path in store:
            check(path, STORE)
    else:
        store = None
    wide, shelf = art / 'topshelf-wide.png', art / 'topshelf.png'
    if not wide.exists():
        fail('topshelf-wide.png (%dx%d) is needed with the icon' % WIDE)
    check(wide, WIDE)
    if shelf.exists():
        check(shelf, SHELF)

    catalog = work / 'Assets.xcassets'
    shutil.rmtree(catalog, ignore_errors=True)
    write(catalog, {})
    brand = catalog / (BRAND + '.brandassets')
    assets = [{'filename': 'App Icon.imagestack', 'idiom': 'tv', 'role': 'primary-app-icon', 'size': '400x240'},
              {'filename': 'Top Shelf Image Wide.imageset', 'idiom': 'tv', 'role': 'top-shelf-image-wide',
               'size': '2320x720'}]
    image_stack(brand / 'App Icon.imagestack', icon, ICON)
    image_set(brand / 'Top Shelf Image Wide.imageset', wide, WIDE)
    if store:
        assets.append({'filename': 'App Icon - App Store.imagestack', 'idiom': 'tv',
                       'role': 'primary-app-icon', 'size': '1280x768'})
        image_stack(brand / 'App Icon - App Store.imagestack', store, STORE, retina=False)
    if shelf.exists():
        assets.append({'filename': 'Top Shelf Image.imageset', 'idiom': 'tv', 'role': 'top-shelf-image',
                       'size': '1920x720'})
        image_set(brand / 'Top Shelf Image.imageset', shelf, SHELF)
    write(brand, {'assets': assets})

    partial = work / 'assets-info.plist'
    result = subprocess.run(['xcrun', 'actool', '--compile', str(app), '--platform', sdk,
                             '--minimum-deployment-target', '17.4', '--target-device', 'tv',
                             '--app-icon', BRAND, '--output-partial-info-plist', str(partial),
                             '--output-format', 'human-readable-text', '--notices', '--warnings',
                             '--errors', str(catalog)], capture_output=True, text=True)
    problems = [line for line in result.stdout.splitlines() if ': error:' in line or ': warning:' in line]
    if result.returncode or any(': error:' in line for line in problems):
        fail('actool failed:\n' + (result.stdout + result.stderr).strip())
    for line in problems:
        print('tvos-art: ' + line.strip(), file=sys.stderr)
    with open(app / 'Info.plist', 'rb') as f:
        info = plistlib.load(f)
    with open(partial, 'rb') as f:
        info.update(plistlib.load(f))
    with open(app / 'Info.plist', 'wb') as f:
        plistlib.dump(info, f)
    print('tvos-art: icon (%d layers)%s and Top Shelf image%s added' % (
        len(icon), ', App Store icon' if store else '', 's' if shelf.exists() else ''))


if __name__ == '__main__':
    main()
