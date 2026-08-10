"""Generate assets/header.svg: an animated ASCII-art rendering of assets/unnamed.jpg
drawn line by line on a plain dark background.

Run: python scripts/generate_ascii_header.py
"""
import html
from pathlib import Path

from PIL import Image, ImageOps

SRC_IMAGE = Path("assets/unnamed.jpg")
OUT_SVG = Path("assets/header.svg")

COLS = 170
CHAR_ASPECT = 0.52          # glyph width / glyph height for the monospace font
FONT_SIZE = 5.4             # px
CELL_W = FONT_SIZE * CHAR_ASPECT
CELL_H = FONT_SIZE * 1.02

RAMP = " .:-=+*#%@"         # dark -> bright (bright pixel = denser glyph)

# crop fractions to trim dead sky/sand and push the face/body into more of the grid
CROP_TOP = 0.42
CROP_BOTTOM = 0.06
CROP_LEFT = 0.27
CROP_RIGHT = 0.29

PAD = 20
SVG_W = 1200


def build_grid():
    im = Image.open(SRC_IMAGE)
    im = ImageOps.exif_transpose(im).convert("L")
    w, h = im.size
    im = im.crop((
        round(w * CROP_LEFT),
        round(h * CROP_TOP),
        round(w * (1 - CROP_RIGHT)),
        round(h * (1 - CROP_BOTTOM)),
    ))
    w, h = im.size
    rows = round(COLS * (h / w) * CHAR_ASPECT)
    im = im.resize((COLS, rows), Image.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=1)
    # lift shadow detail (face/body are backlit) without blowing out the sunset
    gamma = 0.62
    lut = [round(255 * ((i / 255) ** gamma)) for i in range(256)]
    im = im.point(lut)
    px = im.load()
    grid = []
    for y in range(rows):
        row = []
        for x in range(COLS):
            b = px[x, y] / 255.0
            idx = min(len(RAMP) - 1, int(b * (len(RAMP) - 1) + 0.5))
            ch = RAMP[idx]
            opacity = round(0.10 + 0.90 * b, 3)
            row.append((ch, opacity))
        grid.append(row)
    return grid


def esc(ch: str) -> str:
    return html.escape(ch, quote=False)


def main():
    grid = build_grid()
    rows = len(grid)

    art_w = COLS * CELL_W
    art_h = rows * CELL_H
    svg_h = round(art_h + PAD * 2)
    art_x = round((SVG_W - art_w) / 2)
    art_y = PAD

    sweep_span = 4.2      # seconds spent sweeping top -> bottom
    fade_in = 0.35         # seconds for a row to reach full opacity once it starts
    hold_for = 3.6          # seconds the fully-drawn image stays visible
    fade_out = 1.0          # seconds for all rows to fade out together
    cycle = sweep_span + fade_in + hold_for + fade_out + 1.2  # + blank pause before loop

    fade_out_start = sweep_span + fade_in + hold_for
    fade_out_end = fade_out_start + fade_out

    def key_times(delay):
        eps = 1e-4
        t0 = 0.0
        t1 = max(delay, eps)
        t2 = max(delay + fade_in, t1 + eps)
        t3 = max(fade_out_start, t2 + eps)
        t4 = max(fade_out_end, t3 + eps)
        return [t0, t1, t2, t3, t4, cycle]

    text_rows = []
    for i, row in enumerate(grid):
        y = art_y + (i + 1) * CELL_H
        delay = (i / max(1, rows - 1)) * sweep_span
        tspans = []
        cx = art_x
        for ch, opacity in row:
            if ch == " ":
                cx += CELL_W
                continue
            tspans.append(
                f'<tspan x="{cx:.2f}" fill-opacity="{opacity}">{esc(ch)}</tspan>'
            )
            cx += CELL_W
        if not tspans:
            continue
        kt = key_times(delay)
        key_times_attr = ";".join(f"{t / cycle:.5f}" for t in kt)
        text_rows.append(
            f'<text y="{y:.2f}" class="art" opacity="0">' + "".join(tspans) +
            f'<animate attributeName="opacity" values="0;0;1;1;0;0" '
            f'keyTimes="{key_times_attr}" dur="{cycle:.3f}s" begin="0s" '
            f'repeatCount="indefinite"/></text>'
        )

    svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{svg_h}" viewBox="0 0 {SVG_W} {svg_h}" role="img" aria-label="Aaron Chu — ASCII portrait">
<defs>
  <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#010301"/>
    <stop offset="45%" stop-color="#040a04"/>
    <stop offset="100%" stop-color="#081208"/>
  </linearGradient>
  <filter id="neonGlow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="blur"/>
    <feColorMatrix in="blur" type="matrix"
      values="0 0 0 0 0.15  0 0 0 0 1  0 0 0 0 0.35  0 0 0 1 0" result="glow"/>
    <feMerge>
      <feMergeNode in="glow"/>
      <feMergeNode in="SourceGraphic"/>
    </feMerge>
  </filter>
  <style><![CDATA[
    text {{ font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'SF Mono', Consolas, monospace; }}
    .art {{ fill: #39ff14; font-size: {FONT_SIZE}px; filter: url(#neonGlow); }}
  ]]></style>
</defs>

<rect width="{SVG_W}" height="{svg_h}" fill="url(#bgGrad)"/>

{"".join(text_rows)}
</svg>
'''

    OUT_SVG.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT_SVG} ({rows} rows x {COLS} cols, {svg_h}px tall)")


if __name__ == "__main__":
    main()
