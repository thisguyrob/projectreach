# Apple TV art

Put the Apple TV app's icon and Top Shelf image here as PNG files with these names and sizes. The
next `scripts/xbox/build-ios.sh --tvos` (or `--tvos-simulator`) build adds them to the app
(`scripts/xbox/tvos-art.py`). Without them, the app has a blank icon.

| File | Size (pixels) | Needed | What it is |
| --- | --- | --- | --- |
| `icon-back.png` | 800 × 480 | yes | The icon's bottom layer. Opaque: no transparency. |
| `icon-middle.png` | 800 × 480 | no | A middle layer, with transparency around its subject. |
| `icon-front.png` | 800 × 480 | yes | The top layer, with transparency around its subject. |
| `topshelf-wide.png` | 4640 × 1440 | yes | The banner across the top of the Home Screen when the app is in the top row. |
| `topshelf.png` | 3840 × 1440 | no | The older, narrower Top Shelf banner. |
| `appstore-back.png`, `appstore-middle.png`, `appstore-front.png` | 1280 × 768 | no | The App Store icon, one per icon layer. Only for the App Store or TestFlight. |

Give the art at these sizes: the build makes the half-size (1x) copies itself. A file of another
size stops the build and names it.

## The icon's layers

tvOS stacks the layers and moves them against each other when the icon is highlighted, which gives
it depth. Put the background on `icon-back.png` and the subject on `icon-front.png`, with
`icon-middle.png` for something in between.

- tvOS rounds the corners and adds the shadow: draw square corners and no shadow.
- A highlighted icon is enlarged and moves, so its edges get cropped. Keep everything that matters
  away from them.
- The art has to be your own. Don't use Bungie's or Microsoft's Halo artwork or logo.
