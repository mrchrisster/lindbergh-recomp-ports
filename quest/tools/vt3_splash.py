#!/usr/bin/env python3
"""vt3_splash.py <out.c> [preview.png] [--layout A|B|C]: draws the Quest
start-up screen for Virtua Tennis 3 (VR edition) and writes it as a deflated
RGBA image in C for host_xr.c's splash (splash_art.c).

Release rule (owner, 2026-11-12): everything drawn here is our own art - no
Sega logo, texture or font. The game's own title logo is NOT in this file:
the panel leaves a place for it (lg_splash_logo_at), and at start-up
host_xr.c reads the logo from the player's game files and composites it
there with our "VR" badge after it (lindberghrecomp/src/runtime/
splash_logo.c). Without readable game files our own text title "VIRTUA
TENNIS 3 VR" goes there instead.

Design (owner, 2026-11-12: "go away completely from the existing design"):
minimal and spacious; the logo; a left and a right controller drawn as thin
lines (our own simplified drawings) with short callouts to the controls
(xr_controls.c lever_buttons: either hand alike - trigger top spin, A / X
slice, B / Y lob, thumbstick move and click = Start; the grip does nothing;
the left controller's menu button opens the settings); no countdown digits -
a thin line fills with the loading time and a small tennis ball rides on
its end. Layouts (previews for the owner; A is committed, the default -
the owner's pick; --font 1|2|3 the labels' typeface, 1 committed):
  A  centre stage - logo on top, the two controllers side by side under it,
     callouts outwards, the line along the bottom
  B  shared legend - the controllers at the sides, one legend between them
  C  editorial - logo and legend left, the controllers right, the line as a
     full-width baseline

The image is an atlas, top to bottom:
  the panel, PANEL_W x PANEL_H
  a row of cells, CELL_W x CELL_H: cell 10 is the line's solid colour
  a row of parts: the VR badge, the fallback title, the ball
Needs Pillow and the macOS system fonts."""
import sys, zlib, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

LAYOUT = 'A'                    # committed: A (owner's pick, 2026-11-12)
FONT = 1                        # committed: 1 (DIN), see FONTS
args = []
it = iter(sys.argv[1:])
for a in it:
    if a == '--layout':
        LAYOUT = next(it).upper()
    elif a == '--font':
        FONT = int(next(it))
    else:
        args.append(a)

PANEL_W, PANEL_H = 1536, 864
CELL_W, CELL_H = 64, 96
PARTS_H = 260
W, H = PANEL_W, PANEL_H + CELL_H + PARTS_H

F = '/System/Library/Fonts/'
def font(path, size, index=0):
    return ImageFont.truetype(path, int(size), index=index)
HEAVY_I = (F + 'Avenir Next Condensed.ttc', 9)     # Heavy Italic
# the labels' typeface: one family, the action word heavier and larger, the
# control's name lighter and smaller (owner: sportier, scoreboard / arcade
# feel). Apple system fonts, rendered into the picture at build time; for a
# public release swap in an open-licence (OFL) equivalent (e.g. Barlow
# Condensed / Saira Condensed for DIN, Jost for Futura, Archivo Narrow for
# Helvetica Neue Condensed) - not downloaded here.
S_ = F + 'Supplemental/'
FONTS = {
    1: ('DIN', (S_ + 'DIN Condensed Bold.ttf', 0, 36), (S_ + 'DIN Alternate Bold.ttf', 0, 18)),
    2: ('Futura Condensed', (S_ + 'Futura.ttc', 4, 32), (S_ + 'Futura.ttc', 3, 20)),
    3: ('Helvetica Neue Condensed', (F + 'HelveticaNeue.ttc', 9, 31), (F + 'HelveticaNeue.ttc', 10, 18)),
}
FONT_NAME, (_ap, _ai, _as), (_np, _ni, _ns) = FONTS[FONT]
act_f = font(_ap, _as, _ai)
name_f = font(_np, _ns, _ni)
note_f = font(_np, _ns + 1, _ni)
btn_font = lambda size: font(_np, size, _ni)

# the game's own colours (its title screen: navy, chrome white, ball lime, orange)
BG0, BG1 = (12, 26, 62), (3, 7, 20)
LIME = (200, 222, 72)
WHITE = (236, 242, 250)
LINE = (150, 168, 200)
DIM = (110, 126, 158)
FAINT = (40, 56, 96)

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
panel = Image.new('RGBA', (PANEL_W, PANEL_H), BG1 + (255,))
d = ImageDraw.Draw(panel)
for y in range(PANEL_H):
    t = y / PANEL_H
    d.line([(0, y), (PANEL_W, y)], fill=tuple(int(BG0[k] * (1 - t) + BG1[k] * t) for k in range(3)) + (255,))


# ---------------------------------------------------------------- lettering (VR badge, fallback title)
def vgrad(size, stops):
    w, h = size
    col = Image.new('RGBA', (1, 256))
    for y in range(256):
        t = y / 255
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0
                col.putpixel((0, y), tuple(int(c0[i] + (c1[i] - c0[i]) * u) for i in range(3)) + (255,))
                break
    return col.resize((max(1, w), max(1, h)), Image.BILINEAR)

CHROME = [(0, (255, 255, 255)), (.44, (226, 232, 240)), (.52, (170, 180, 196)), (.64, (236, 240, 246)), (1, (196, 202, 214))]
LIMEG = [(0, (255, 255, 230)), (.45, (240, 250, 190)), (.52, LIME), (1, (120, 150, 20))]

def shifted(m, dx, dy):
    o = Image.new('L', m.size, 0); o.paste(m, (int(dx), int(dy))); return o

def lettering(text, size, stops=CHROME):
    """arcade-style lettering: gradient fill, dark keyline, white rim, bevel, soft shadow"""
    f = font(HEAVY_I[0], size, HEAVY_I[1])
    rim, key = max(4, size // 14), max(3, size // 22)
    pb = ImageDraw.Draw(Image.new('L', (1, 1))).textbbox((0, 0), text, font=f, stroke_width=rim)
    w, h = pb[2] - pb[0] + 40, pb[3] - pb[1] + 40
    at = (20 - pb[0], 20 - pb[1])
    def mask(stroke=0):
        m = Image.new('L', (w, h), 0)
        ImageDraw.Draw(m).text(at, text, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
        return m
    full, mrim, mkey = mask(), mask(rim), mask(key)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sh.putalpha(shifted(mrim, size * .02, size * .05).filter(ImageFilter.GaussianBlur(size * .03)).point(lambda v: v * 190 // 255))
    out.alpha_composite(sh)
    for m, c in ((mrim, WHITE), (mkey, (6, 8, 18))):
        lay = Image.new('RGBA', (w, h), c + (255,)); lay.putalpha(m); out.alpha_composite(lay)
    bb = full.getbbox()
    body = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    body.paste(vgrad((w, bb[3] - bb[1]), stops), (0, bb[1]))
    body.putalpha(ImageChops.multiply(body.getchannel('A'), full))
    out.alpha_composite(body)
    dd = max(1, size // 60)
    for m, c, al in ((ImageChops.subtract(full, shifted(full, dd, dd)), (255, 255, 255), 150),
                     (ImageChops.subtract(full, shifted(full, -dd, -dd)), (0, 10, 40), 110)):
        lay = Image.new('RGBA', (w, h), c + (0,))
        lay.putalpha(ImageChops.multiply(m.filter(ImageFilter.GaussianBlur(dd * .6)).point(lambda v: v * al // 255), full))
        out.alpha_composite(lay)
    return out.crop(out.getbbox())


# ---------------------------------------------------------------- a controller, thin lines (our own drawing)
def controller(cx, cy, s, left):
    """A Quest-style controller seen from above, simplified: a rounded head,
    the handle below it, the trigger as a tab behind the head's top edge,
    the thumbstick on the outer side, the two buttons on the inner side (and
    the left one's menu button under them). s = scale (1 = ~320 px tall).
    Returns the controls' anchor points."""
    k = -1 if left else 1               # outer side: -1 left, +1 right
    lw = max(2, int(3 * s))
    P = lambda x, y: (cx + x * s, cy + y * s)
    d.rounded_rectangle([*P(-34, -132), *P(34, -100)], radius=14 * s, outline=LIME + (255,), width=lw, fill=BG0 + (255,))
    d.rounded_rectangle([*P(-100 + 8 * k, -112), *P(100 + 8 * k, 46)], radius=78 * s, outline=LINE + (255,), width=lw, fill=BG0 + (255,))
    hb = [P(-46, 36), P(46, 36), P(34 + 22 * k, 168), P(-34 + 22 * k, 168)]
    d.line([hb[0], hb[3]], fill=LINE + (255,), width=lw)
    d.line([hb[1], hb[2]], fill=LINE + (255,), width=lw)
    d.arc([*P(-34 + 22 * k, 146), *P(34 + 22 * k, 190)], 0, 180, fill=LINE + (255,), width=lw)
    sx, sy = 40 * k, -40
    d.ellipse([*P(sx - 30, sy - 30), *P(sx + 30, sy + 30)], outline=LIME + (255,), width=lw)
    d.ellipse([*P(sx - 15, sy - 15), *P(sx + 15, sy + 15)], outline=LINE + (255,), width=max(1, lw - 1))
    names = ('X', 'Y') if left else ('A', 'B')
    lo, up = P(-38 * k, -6), P(-24 * k, -58)
    br = 17 * s
    for (x, y), n in ((lo, names[0]), (up, names[1])):
        d.ellipse([x - br, y - br, x + br, y + br], outline=LIME + (255,), width=lw)
        d.text((x, y + 1), n, font=btn_font(max(10, 17 * s)), fill=WHITE + (255,), anchor='mm')
    marks = {'trigger': P(0, -116), 'stick': P(sx, sy), 'lower': lo, 'upper': up, 'r_btn': br, 'r_stick': 30 * s}
    if left:
        mx, my = P(-6, 26)
        mr = 10 * s
        d.ellipse([mx - mr, my - mr, mx + mr, my + mr], outline=LIME + (255,), width=max(1, lw - 1))
        for j in (-3, 0, 3):
            d.line([(mx - 5 * s, my + j * s), (mx + 5 * s, my + j * s)], fill=WHITE + (255,), width=max(1, int(1.5 * s)))
        marks['menu'] = (mx, my)
    else:
        mx, my = P(6, 26)                              # the system button: drawn, not used
        d.ellipse([mx - 9 * s, my - 9 * s, mx + 9 * s, my + 9 * s], outline=DIM + (255,), width=max(1, lw - 1))
    return marks


def callout(pt, r, tx, ty, act, name, side):
    """a thin leader from a control to its label: the action (lime caps), the control (small grey).
    side -1: label left of tx (right-aligned), +1: right"""
    x, y = pt
    ex = tx - 12 * side
    dx, dy = ex - x, ty - y
    n = math.hypot(dx, dy) or 1
    d.line([(x + dx / n * (r + 4), y + dy / n * (r + 4)), (ex, ty)], fill=DIM + (255,), width=2)
    d.ellipse([ex - 3, ty - 3, ex + 3, ty + 3], fill=LIME + (255,))
    a = 'rm' if side < 0 else 'lm'
    d.text((tx, ty - 1), act, font=act_f, fill=LIME + (255,), anchor=a.replace('m', 's'))
    d.text((tx, ty + 6), name, font=name_f, fill=LINE + (255,), anchor=a.replace('m', 'a'))


# ---------------------------------------------------------------- parts: VR badge, fallback title, ball
vr = lettering('VR', 120)
VR_W, VR_H = vr.size
t1 = lettering('VIRTUA TENNIS 3', 96)
t2 = lettering('VR', 96, LIMEG)
TITLE_W, TITLE_H = t1.size[0] + 18 + t2.size[0], max(t1.size[1], t2.size[1])
title = Image.new('RGBA', (TITLE_W, TITLE_H), (0, 0, 0, 0))
title.alpha_composite(t1, (0, 0)); title.alpha_composite(t2, (t1.size[0] + 18, 0))

BALL, SS = 30, 8
bimg = Image.new('RGBA', (BALL * SS, BALL * SS), (0, 0, 0, 0))
bd = ImageDraw.Draw(bimg)
R = BALL * SS / 2 - 2
bd.ellipse([2, 2, BALL * SS - 2, BALL * SS - 2], fill=LIME + (255,))
for s_ in (-1, 1):
    o = BALL * SS / 2 + s_ * R * 1.3
    bd.ellipse([o - R, BALL * SS / 2 - R * 1.08, o + R, BALL * SS / 2 + R * 1.08], outline=(250, 252, 240, 255), width=int(R * .14))
m = Image.new('L', bimg.size, 0); ImageDraw.Draw(m).ellipse([2, 2, BALL * SS - 2, BALL * SS - 2], fill=255)
bimg.putalpha(ImageChops.multiply(bimg.getchannel('A'), m))
bimg = bimg.rotate(-25, resample=Image.BICUBIC).resize((BALL, BALL), Image.LANCZOS)


# ---------------------------------------------------------------- layouts
LEFT_MAP = [('trigger', 'TOP SPIN', 'trigger'), ('upper', 'LOB', 'Y'), ('stick', 'MOVE', 'stick - click: Start'),
            ('lower', 'SLICE', 'X'), ('menu', 'SETTINGS', 'menu button')]
RIGHT_MAP = [('trigger', 'TOP SPIN', 'trigger'), ('upper', 'LOB', 'B'), ('stick', 'MOVE', 'stick - click: Start'),
             ('lower', 'SLICE', 'A')]

def radius(marks, key):
    return {'trigger': 4, 'stick': marks['r_stick'], 'lower': marks['r_btn'], 'upper': marks['r_btn'], 'menu': 10}[key]

if LAYOUT == 'A':
    LOGO_AT = (360, 46, 640, 274)
    VR_AT = (-6, -18)
    TITLE_AT = ((PANEL_W - TITLE_W) // 2, 46 + (274 - TITLE_H) // 2)
    cy = 560
    L = controller(616, cy, .9, True)
    Rm = controller(920, cy, .9, False)
    ys = [cy - 150 + 66 * i for i in range(5)]          # evenly spaced
    for (key, act, name), ty in zip(LEFT_MAP, ys):
        callout(L[key], radius(L, key), 400, ty, act, name, -1)
    for (key, act, name), ty in zip(RIGHT_MAP, ys):
        callout(Rm[key], radius(Rm, key), 1136, ty, act, name, 1)
    d.text((PANEL_W // 2, cy + 196), 'either hand plays - the grip is not used', font=note_f, fill=DIM + (255,), anchor='mm')
    BAR = (568, 806, 968, 809)
    d.text((PANEL_W // 2, 834), 'loading', font=note_f, fill=DIM + (255,), anchor='mm')
elif LAYOUT == 'B':
    LOGO_AT = (380, 40, 600, 250)
    VR_AT = (-6, -16)
    TITLE_AT = ((PANEL_W - TITLE_W) // 2, 40 + (250 - TITLE_H) // 2)
    cy = 560
    L = controller(300, cy, 1.0, True)
    Rm = controller(1236, cy, 1.0, False)
    # either hand alike: one legend, a faint leader from each controller
    rows = [('TOP SPIN', 'trigger', 'trigger'), ('LOB', 'B / Y', 'upper'), ('MOVE', 'thumbstick  -  click: Start', 'stick'),
            ('SLICE', 'A / X', 'lower'), ('SETTINGS', 'left menu button', 'menu')]
    for i, (act, name, key) in enumerate(rows):
        ty = cy - 150 + i * 70
        d.text((PANEL_W // 2, ty - 10), act, font=act_f, fill=LIME + (255,), anchor='mm')
        d.text((PANEL_W // 2, ty + 16), name, font=name_f, fill=DIM + (255,), anchor='mm')
        for M, sgn in ((L, -1), (Rm, 1)):
            if key not in M: continue
            x, y = M[key]
            ex = PANEL_W // 2 + sgn * 150
            r = radius(M, key)
            n = math.hypot(ex - x, ty - y) or 1
            d.line([(x + (ex - x) / n * (r + 4), y + (ty - y) / n * (r + 4)), (ex, ty)], fill=FAINT + (255,), width=2)
            d.ellipse([ex - 3, ty - 3, ex + 3, ty + 3], fill=LIME + (255,))
    BAR = (568, 812, 968, 815)
else:
    LOGO_AT = (90, 60, 620, 250)
    VR_AT = (-6, -16)
    if TITLE_W > 860:
        title = title.resize((860, int(TITLE_H * 860 / TITLE_W)), Image.LANCZOS); TITLE_W, TITLE_H = title.size
    TITLE_AT = (90, 60 + (250 - TITLE_H) // 2)
    rows = [('TOP SPIN', 'trigger'), ('SLICE', 'A or X'), ('LOB', 'B or Y'), ('MOVE', 'thumbstick  -  click: Start'),
            ('SETTINGS', 'menu button (left)')]
    for i, (act, name) in enumerate(rows):
        ty = 420 + i * 62
        d.text((120, ty), act, font=act_f, fill=LIME + (255,), anchor='lm')
        d.text((300, ty + 2), name, font=name_f, fill=LINE + (255,), anchor='lm')
        d.line([(120, ty + 28), (560, ty + 28)], fill=FAINT + (255,), width=1)
    controller(1000, 460, 1.05, True)
    controller(1290, 460, 1.05, False)
    d.text((1145, 700), 'either hand plays', font=note_f, fill=DIM + (255,), anchor='mm')
    BAR = (90, 806, 1446, 808)

d.rectangle([BAR[0], BAR[1], BAR[2], BAR[3]], fill=FAINT + (255,))
img.alpha_composite(panel, (0, 0))

# the cells row: cell 10 = the line's colour (no digits: lg_splash_digits height 0)
ImageDraw.Draw(img).rectangle([10 * CELL_W + 8, PANEL_H + 8, 11 * CELL_W - 8, PANEL_H + CELL_H - 8], fill=LIME + (255,))

PY = PANEL_H + CELL_H
assert VR_H <= PARTS_H and TITLE_H <= PARTS_H and VR_W + TITLE_W + BALL + 24 <= W, (VR_W, VR_H, TITLE_W, TITLE_H)
VR = (0, PY, VR_W, VR_H)
TITLE = (VR_W + 8, PY, TITLE_W, TITLE_H)
BALLR = (VR_W + 8 + TITLE_W + 8, PY, BALL, BALL)
img.alpha_composite(vr, VR[:2]); img.alpha_composite(title, TITLE[:2]); img.alpha_composite(bimg, BALLR[:2])

raw = img.tobytes()
z = zlib.compress(raw, 9)
with open(args[0], 'w') as f:
    f.write('/* Generated by quest/tools/vt3_splash.py (layout %s, font %d: %s) - original artwork for the\n' % (LAYOUT, FONT, FONT_NAME))
    f.write(' * Quest start-up screen (host_xr.c). Do not edit; run the script.\n'
            ' * No game art: the title logo is read from the player\'s game files at\n'
            ' * start-up and composited into lg_splash_logo_at (splash_logo.c). */\n')
    f.write('#include <stddef.h>\n')
    f.write(f'const int lg_splash_w = {W}, lg_splash_h = {H}, lg_splash_panel_h = {PANEL_H};\n')
    f.write(f'const int lg_splash_cell[2] = {{ {CELL_W}, {CELL_H} }};\n')
    f.write('const int lg_splash_digits[3] = { 0, 0, 0 };   /* no countdown digits */\n')
    f.write(f'const int lg_splash_bar[4] = {{ {BAR[0]}, {BAR[1]}, {BAR[2]}, {BAR[3]} }};\n')
    f.write(f'const int lg_splash_ball[4] = {{ {BALLR[0]}, {BALLR[1]}, {BALLR[2]}, {BALLR[3]} }};   /* rides on the line\'s end */\n')
    f.write(f'const int lg_splash_logo_at[4] = {{ {LOGO_AT[0]}, {LOGO_AT[1]}, {LOGO_AT[2]}, {LOGO_AT[3]} }};   /* the logo\'s place: x, y, w, h */\n')
    f.write(f'const int lg_splash_vr[4] = {{ {VR[0]}, {VR[1]}, {VR[2]}, {VR[3]} }};   /* the VR badge in the atlas */\n')
    f.write(f'const int lg_splash_vr_at[2] = {{ {VR_AT[0]}, {VR_AT[1]} }};   /* from the fitted logo\'s bottom right */\n')
    f.write(f'const int lg_splash_title[4] = {{ {TITLE[0]}, {TITLE[1]}, {TITLE[2]}, {TITLE[3]} }};   /* our own title in the atlas */\n')
    f.write(f'const int lg_splash_title_at[2] = {{ {TITLE_AT[0]}, {TITLE_AT[1]} }};   /* where it goes without the logo */\n')
    f.write('const char lg_splash_logo_file[] = "resource/sprite/I_ADV_titlelogo_us_KB.abr";   /* the player\'s, in the game folder */\n')
    f.write(f'const size_t lg_splash_zlen = {len(z)};\n')
    f.write('const unsigned char lg_splash_z[] = {\n')
    for i in range(0, len(z), 24):
        f.write(''.join(f'{b},' for b in z[i:i + 24]) + '\n')
    f.write('};\n')
print(f'layout {LAYOUT}, font {FONT} ({FONT_NAME}): {W}x{H}, {len(raw)} bytes -> {len(z)} deflated')
if len(args) > 1:       # the panel without game files (our title), the line at 40 %
    prev = img.crop((0, 0, PANEL_W, PANEL_H))
    prev.alpha_composite(title, TITLE_AT)
    x1 = BAR[0] + (BAR[2] - BAR[0]) * .4
    ImageDraw.Draw(prev).rectangle([BAR[0], BAR[1], x1, BAR[3]], fill=LIME + (255,))
    prev.alpha_composite(bimg, (int(x1 - BALL / 2), int((BAR[1] + BAR[3]) / 2 - BALL / 2)))
    prev.save(args[1])
