#!/usr/bin/env python3
"""vt3_splash.py <out.c> [preview.png]: draws the Quest start-up screen for
Virtua Tennis 3 (VR edition) - original artwork, no Sega or game art - and
writes it as a deflated RGBA image in C for host_xr.c's splash (xr_splash.c).

The image is an atlas, top to bottom:
  the panel, PANEL_W x PANEL_H: title, controller map, the countdown's frame
  a row of cells: the digits 0-9 (white on clear) and a solid white cell
The countdown's digits and the progress bar are drawn over the panel as
their own layers from those cells, at the places written into the C file.
Needs Pillow and the macOS system fonts."""
import sys, zlib, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PANEL_W, PANEL_H = 1536, 864
CELL_W, CELL_H = 64, 96
W, H = PANEL_W, PANEL_H + CELL_H

F = '/System/Library/Fonts/'
S = F + 'Supplemental/'
def font(path, size, index=0):
    return ImageFont.truetype(path, size, index=index)

title_f = font(F + 'Avenir Next Condensed.ttc', 150, 8)     # Heavy Italic
sub_f = font(F + 'Avenir Next Condensed.ttc', 54, 6)        # Demi Bold Italic
label_f = font(F + 'Avenir Next.ttc', 30, 2)                # Demi Bold
small_f = font(F + 'Avenir Next.ttc', 24, 0)
digit_f = font(S + 'DIN Condensed Bold.ttf', 104)
btn_f = font(F + 'Avenir Next.ttc', 22, 2)

BG0, BG1 = (6, 14, 34), (2, 4, 10)
ACCENT = (198, 232, 58)          # tennis-ball yellow-green
COURT = (40, 92, 170)
WHITE = (240, 244, 250)
GREY = (150, 160, 178)
BODY = (34, 38, 48)
FACE = (52, 58, 72)
EDGE = (110, 118, 136)

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
panel = Image.new('RGBA', (PANEL_W, PANEL_H), BG1 + (255,))
d = ImageDraw.Draw(panel)

# background: vertical gradient, faint court lines in perspective
for y in range(PANEL_H):
    t = y / PANEL_H
    c = tuple(int(BG0[k] * (1 - t) + BG1[k] * t) for k in range(3))
    d.line([(0, y), (PANEL_W, y)], fill=c + (255,))
lines = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
ld = ImageDraw.Draw(lines)
vx, vy = PANEL_W / 2, -900           # vanishing point above the panel
for x in (-1400, -900, -520, 520, 900, 1400):
    ld.line([(vx, vy), (vx + x * 1.6, PANEL_H + 200)], fill=COURT + (70,), width=3)
for y in (520, 700):
    ld.line([(0, y), (PANEL_W, y)], fill=COURT + (55,), width=3)
panel.alpha_composite(lines)

# a tennis ball, top left, with its seam
def ball(cx, cy, r):
    glow = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5], fill=ACCENT + (60,))
    panel.alpha_composite(glow.filter(ImageFilter.GaussianBlur(r * 0.4)))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT + (255,))
    d.ellipse([cx - r * .55, cy - r * .7, cx + r * .1, cy - r * .1], fill=(230, 250, 140, 255))   # highlight
    d.ellipse([cx - r * .5, cy - r * .62, cx + r * .02, cy - r * .18], fill=ACCENT + (255,))
    seam = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(seam)
    for s in (-1, 1):       # two arcs bulging towards each other, as a ball's seam looks
        ox = cx + s * r * 1.35
        sd.ellipse([ox - r, cy - r * 1.05, ox + r, cy + r * 1.05], outline=WHITE + (255,), width=max(3, r // 9))
    mask = Image.new('L', (PANEL_W, PANEL_H), 0)
    ImageDraw.Draw(mask).ellipse([cx - r + 2, cy - r + 2, cx + r - 2, cy + r - 2], fill=255)
    clipped = Image.new('RGBA', (PANEL_W, PANEL_H), (0, 0, 0, 0))
    clipped.paste(seam, (0, 0), mask)
    panel.alpha_composite(clipped)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(150, 180, 40, 255), width=3)

ball(206, 170, 92)

# title
d.text((340, 52), 'VIRTUA TENNIS 3', font=title_f, fill=WHITE + (255,))
tw = d.textlength('VIRTUA TENNIS 3', font=title_f)
d.rectangle([344, 232, 340 + tw, 238], fill=ACCENT + (255,))
d.text((346, 246), 'VR EDITION', font=sub_f, fill=ACCENT + (255,))
d.text((346 + d.textlength('VR EDITION  ', font=sub_f), 262), 'for Meta Quest 3', font=small_f, fill=GREY + (255,))

# controllers: a plain drawing of each, face up, labels either side
def controller(cx, cy, left):
    s = -1 if left else 1
    # ring-less head and handle
    d.rounded_rectangle([cx - 120, cy - 110, cx + 120, cy + 70], radius=80, fill=BODY + (255,), outline=EDGE + (255,), width=3)
    d.polygon([(cx - 70, cy + 40), (cx + 70, cy + 40), (cx + 50 + s * 20, cy + 170), (cx - 50 + s * 20, cy + 170)], fill=BODY + (255,))
    d.ellipse([cx - 50 + s * 20, cy + 148, cx + 50 + s * 20, cy + 192], fill=BODY + (255,), outline=EDGE + (255,), width=3)
    d.line([(cx - 70, cy + 52), (cx - 50 + s * 20, cy + 170)], fill=EDGE + (255,), width=3)
    d.line([(cx + 70, cy + 52), (cx + 50 + s * 20, cy + 170)], fill=EDGE + (255,), width=3)
    d.rounded_rectangle([cx - 104, cy - 94, cx + 104, cy + 54], radius=64, fill=FACE + (255,))
    # trigger, seen past the top edge
    d.rounded_rectangle([cx - 46, cy - 136, cx + 46, cy - 104], radius=14, fill=(70, 76, 92, 255), outline=ACCENT + (255,), width=3)
    # thumbstick (inner side) and two buttons (outer side)
    sx = cx - s * 44
    d.ellipse([sx - 34, cy - 54, sx + 34, cy + 14], fill=(24, 26, 32, 255), outline=ACCENT + (255,), width=3)
    d.ellipse([sx - 20, cy - 40, sx + 20, cy], fill=(60, 64, 76, 255))
    bx = cx + s * 50
    names = ('X', 'Y') if left else ('A', 'B')
    pos = [(bx - s * 4, cy + 2), (bx + s * 14, cy - 50)]
    for (x, y), n in zip(pos, names):
        used = n != 'Y'
        d.ellipse([x - 21, y - 21, x + 21, y + 21], fill=(24, 26, 32, 255), outline=(ACCENT if used else EDGE) + (255,), width=3)
        d.text((x, y), n, font=btn_f, fill=(WHITE if used else GREY) + (255,), anchor='mm')
    marks = {'stick': (sx, cy - 20, 36), 'trigger': (cx, cy - 120, 0), names[0]: (*pos[0], 23)}
    if left:
        marks['menu'] = (cx + 6, cy + 35, 13)
        d.ellipse([cx - 6, cy + 24, cx + 18, cy + 46], fill=(24, 26, 32, 255), outline=ACCENT + (255,), width=2)
        d.line([(cx + 1, cy + 31), (cx + 11, cy + 31)], fill=WHITE + (255,), width=2)
        d.line([(cx + 1, cy + 35), (cx + 11, cy + 35)], fill=WHITE + (255,), width=2)
        d.line([(cx + 1, cy + 39), (cx + 11, cy + 39)], fill=WHITE + (255,), width=2)
    else:
        marks[names[1]] = (*pos[1], 23)
    return marks

def label(mark, tx, ty, head, sub, right_side):
    x, y, rad = mark if len(mark) == 3 else (*mark, 0)
    dx, dy = (tx - 14 if right_side else tx + 14) - x, ty + 18 - y
    n = math.hypot(dx, dy) or 1
    x, y = x + dx / n * rad, y + dy / n * rad
    ex = tx - 14 if right_side else tx + 14
    d.line([(x, y), (ex, ty + 18)], fill=GREY + (255,), width=2)
    d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=ACCENT + (255,))
    a = 'la' if right_side else 'ra'
    d.text((tx, ty), head, font=label_f, fill=WHITE + (255,), anchor=a)
    if sub:
        d.text((tx, ty + 36), sub, font=small_f, fill=GREY + (255,), anchor=a)

cy = 450
L = controller(560, cy, True)
R = controller(976, cy, False)
d.text((560, cy + 222), 'LEFT', font=small_f, fill=GREY + (255,), anchor='mm')
d.text((976, cy + 222), 'RIGHT', font=small_f, fill=GREY + (255,), anchor='mm')
label(L['trigger'], 400, 312, 'Trigger  LOB', None, False)
label(L['stick'], 400, 392, 'Thumbstick  MOVE', 'press: Start', False)
label(L['X'], 400, 486, 'X  SLICE', None, False)
label(L['menu'], 400, 552, 'Menu  SETTINGS', 'replays, overlays, screen size', False)
label(R['trigger'], 1136, 312, 'Trigger  TOPSPIN', 'and confirm in menus', True)
label(R['stick'], 1136, 392, 'Thumbstick  MOVE', 'press: Start', True)
label(R['B'], 1136, 476, 'B  SLICE', None, True)
label(R['A'], 1136, 540, 'A  LOB', None, True)

# the countdown's frame: "STARTING IN" [digits] "s", a bar under it
BAR = (468, 800, 1068, 816)            # the bar's trough, x0 y0 x1 y1
DIG = (800, 704)                       # top left of the first digit cell on the panel
DIG_H = 72                             # digit height as drawn there
d.text((780, 714), 'STARTING IN', font=label_f, fill=GREY + (255,), anchor='ra')
d.text((DIG[0] + 2 * DIG_H * CELL_W // CELL_H + 8, 714), 'SECONDS', font=label_f, fill=GREY + (255,))
d.text((PANEL_W // 2, 836), 'Loading the game - your view is set when it starts', font=small_f, fill=GREY + (255,), anchor='ma')
d.rounded_rectangle(BAR, radius=8, fill=(30, 36, 50, 255))

img.alpha_composite(panel, (0, 0))

# the cells: digits 0-9, then solid white
cells = ImageDraw.Draw(img)
for k in range(10):
    x = k * CELL_W
    cells.text((x + CELL_W // 2, PANEL_H + CELL_H // 2 + 4), str(k), font=digit_f, fill=WHITE + (255,), anchor='mm')
cells.rectangle([10 * CELL_W + 8, PANEL_H + 8, 11 * CELL_W - 8, PANEL_H + CELL_H - 8], fill=ACCENT + (255,))

raw = img.tobytes()
z = zlib.compress(raw, 9)
with open(sys.argv[1], 'w') as f:
    f.write('/* Generated by quest/tools/vt3_splash.py - original artwork for the\n'
            ' * Quest start-up screen (xr_splash.c). Do not edit; run the script. */\n')
    f.write('#include <stddef.h>\n')
    f.write(f'const int lg_splash_w = {W}, lg_splash_h = {H}, lg_splash_panel_h = {PANEL_H};\n')
    f.write(f'const int lg_splash_cell[2] = {{ {CELL_W}, {CELL_H} }};\n')
    f.write(f'const int lg_splash_digits[3] = {{ {DIG[0]}, {DIG[1]}, {DIG_H} }};   /* first digit: left, top, height on the panel */\n')
    f.write(f'const int lg_splash_bar[4] = {{ {BAR[0]}, {BAR[1]}, {BAR[2]}, {BAR[3]} }};\n')
    f.write(f'const size_t lg_splash_zlen = {len(z)};\n')
    f.write('const unsigned char lg_splash_z[] = {\n')
    for i in range(0, len(z), 24):
        f.write(''.join(f'{b},' for b in z[i:i + 24]) + '\n')
    f.write('};\n')
print(f'{W}x{H}, {len(raw)} bytes -> {len(z)} deflated')
if len(sys.argv) > 2:
    prev = img.copy()
    pd = ImageDraw.Draw(prev)
    # preview with "32" and a 40 % bar, as the headset shows it
    for i, ch in enumerate('32'):
        k = int(ch); cw = DIG_H * CELL_W // CELL_H
        cell = img.crop((k * CELL_W, PANEL_H, (k + 1) * CELL_W, PANEL_H + CELL_H)).resize((cw, DIG_H))
        prev.alpha_composite(cell, (DIG[0] + i * cw, DIG[1]))
    pd.rounded_rectangle([BAR[0], BAR[1], BAR[0] + (BAR[2] - BAR[0]) * 0.4, BAR[3]], radius=8, fill=ACCENT + (255,))
    prev.save(sys.argv[2])
