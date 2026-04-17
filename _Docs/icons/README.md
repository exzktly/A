# All-Well icon concepts

Three candidate app icons for AllWell.app. All are 1024×1024 SVGs on the macOS
squircle safe-area (rounded rect, 200px corner radius).

| File | Concept | Visual hook |
|------|---------|-------------|
| `icon_1_plate_grid.svg` | **Plate Grid** | A 96-well plate (8×12) with wells lit in DAPI blue / GFP green / mCherry red — the app's native canvas. |
| `icon_2_stardist_nucleus.svg` | **StarDist Nucleus** | A single glowing nucleus inside a star polygon and a dark well — the segmentation-pipeline output. |
| `icon_3_channels_curve.svg` | **Channels & Curve** | Three overlapping channel circles behind a CDF curve crossing a dashed threshold — the Review tab's analysis UI. |

To preview, open any `.svg` directly in a browser or Finder. To produce a macOS
`.icns` bundle from a chosen concept:

```sh
# Render PNGs at the sizes macOS expects, then compose an .iconset.
mkdir AllWell.iconset
for sz in 16 32 64 128 256 512 1024; do
  qlmanage -t -s $sz -o AllWell.iconset icon_1_plate_grid.svg
done
iconutil -c icns AllWell.iconset
```
