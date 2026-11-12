#!/usr/bin/env python3
"""vt3_icon.py [--candidate N] --out DIR [--sheet PNG [--sheet-of 5,6,7]] [--install]

Draws the launcher icon of the Virtua Tennis 3 (VR edition) Quest port:
original artwork in the start-up splash's palette (quest/tools/vt3_splash.py),
drawn with Pillow - no Sega logo, box art, game textures or likenesses.

Candidates (1-7; the default and installed one is 7; the balls of 5-7 have no
specular spot - owner, 2026-11-12):
  5  VT3 chrome  - bold italic "VT3" (pearl VT, deep blue 3, black keyline,
                   white rim, bevel, drop shadow) in front of a glossy tennis
                   ball, on navy - the owner's brief (2026-11-12): "simply VT3
                   with a tennis ball behind it, shaded like the game"
  6  VT3 lime    - the same with white-to-lime letters and a navy keyline
  7  VT3 orange  - white-to-orange letters on the court's blue
  older ones, still selectable:
  1  ball 3      - a tennis ball filling the tile, a big navy "3" across it
  2  headset     - a VR headset whose front plate is a tennis ball, on navy
  3  court       - a court in perspective with a ball over the net
  4  racket      - a racket and ball, diagonal, on navy

DIR gets:
  icon_1024.png                          the master, 1024 x 1024
  drawable-{m,h,xh,xxh,xxxh}dpi/ic_launcher.png      48/72/96/144/192 legacy icons
  adaptive/ic_launcher_{foreground,background}.png   432 x 432 layers (108 dp at
                                         xxxhdpi, the art inside the 66 dp safe zone)
--install writes the five legacy PNGs into quest/vt3/src/main/res/drawable-*/
(where the manifest's android:icon="@drawable/ic_launcher" points).
--sheet PNG writes a contact sheet of the candidates instead (ignores
--candidate; --sheet-of picks some, --sheet-sizes the sizes, default
512,192,96,48 px): dark and light backgrounds, square / rounded-square /
circle masks.
Deterministic, no network. Needs Pillow and the macOS system fonts."""
import argparse, os, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

F = '/System/Library/Fonts/'
HEAVY = (F + 'Avenir Next Condensed.ttc', 8)        # Avenir Next Condensed Heavy
HEAVY_I = (F + 'Avenir Next Condensed.ttc', 9)      # Heavy Italic
LABEL = (F + 'Avenir Next.ttc', 2)                  # Avenir Next Demi Bold

# the splash's palette
BG0, BG1 = (6, 14, 34), (2, 4, 10)
NAVY = (12, 24, 54)
ACCENT = (198, 232, 58)          # tennis-ball yellow-green
ACC_HI = (232, 250, 140)
ACC_LO = (150, 180, 40)
COURT = (40, 92, 170)
COURT_D = (24, 58, 116)
WHITE = (240, 244, 250)
BODY = (34, 38, 48)
FACE = (52, 58, 72)
EDGE = (110, 118, 136)

SS = 2                           # supersampling factor for every render
DENS = {'mdpi': 48, 'hdpi': 72, 'xhdpi': 96, 'xxhdpi': 144, 'xxxhdpi': 192}
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def font(spec, size):
    return ImageFont.truetype(spec[0], max(1, int(size)), index=spec[1])


class Art:
    """A square canvas of S px. Art coordinates are in units of the tile
    (0..1); k shrinks the art about the centre (k < 1 for the adaptive
    foreground, so the art sits inside the safe zone)."""
    def __init__(self, S, k=1.0):
        self.S, self.k = S, k
        self.img = Image.new('RGBA', (S, S), (0, 0, 0, 0))

    def x(self, u):
        return self.S / 2 + (u - 0.5) * self.S * self.k

    def r(self, u):
        return u * self.S * self.k

    def box(self, x0, y0, x1, y1):
        return [self.x(x0), self.x(y0), self.x(x1), self.x(y1)]

    def pts(self, ps):
        return [(self.x(a), self.x(b)) for a, b in ps]

    def layer(self):
        return Image.new('RGBA', (self.S, self.S), (0, 0, 0, 0))

    def put(self, lay, mask=None):
        if mask is not None:
            a = ImageChops.multiply(lay.getchannel('A'), mask)
            lay = lay.copy()
            lay.putalpha(a)
        self.img.alpha_composite(lay)

    def mask(self):
        return Image.new('L', (self.S, self.S), 0)


# ---------------------------------------------------------------- pieces

def navy_bg(a):
    """the splash's vertical navy gradient, full bleed"""
    d = ImageDraw.Draw(a.img)
    for y in range(a.S):
        t = y / a.S
        c = tuple(int(BG0[i] * (1 - t * .7) + BG1[i] * t * .7) for i in range(3))
        d.line([(0, y), (a.S, y)], fill=c + (255,))
    # a soft lighter centre so the art doesn't sit in a black hole
    glow = a.layer()
    ImageDraw.Draw(glow).ellipse([a.S * .1, a.S * .05, a.S * .9, a.S * .85], fill=(30, 52, 100, 120))
    a.img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(a.S * .12)))


def ball(a, cx, cy, r, seam_w=0.085, outline=True, glow=True, tilt=0):
    """tennis ball (art units): yellow-green disc, two white seam arcs"""
    if glow:
        g = a.layer()
        ImageDraw.Draw(g).ellipse(a.box(cx - r * 1.35, cy - r * 1.35, cx + r * 1.35, cy + r * 1.35), fill=ACCENT + (70,))
        a.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(a.r(r * .35))))
    lay = a.layer()
    d = ImageDraw.Draw(lay)
    d.ellipse(a.box(cx - r, cy - r, cx + r, cy + r), fill=ACCENT + (255,))
    # soft highlight, upper left
    hl = a.layer()
    ImageDraw.Draw(hl).ellipse(a.box(cx - r * .75, cy - r * .85, cx + r * .05, cy - r * .05), fill=ACC_HI + (150,))
    lay.alpha_composite(hl.filter(ImageFilter.GaussianBlur(a.r(r * .18))))
    # shade, lower right
    sh = a.layer()
    ImageDraw.Draw(sh).ellipse(a.box(cx - r * .1, cy - r * .1, cx + r * 1.3, cy + r * 1.3), fill=ACC_LO + (140,))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur(a.r(r * .3))))
    # seam: two arcs bulging towards each other
    seam = a.layer()
    sd = ImageDraw.Draw(seam)
    w = max(2, int(a.r(r * seam_w)))
    for s in (-1, 1):
        ox = cx + s * r * 1.32
        sd.ellipse(a.box(ox - r, cy - r * 1.08, ox + r, cy + r * 1.08), outline=WHITE + (255,), width=w)
    if tilt:
        seam = seam.rotate(tilt, center=(a.x(cx), a.x(cy)), resample=Image.BICUBIC)
    lay.alpha_composite(seam)
    m = a.mask()
    ImageDraw.Draw(m).ellipse(a.box(cx - r, cy - r, cx + r, cy + r), fill=255)
    a.put(lay, m)
    if outline:
        ImageDraw.Draw(a.img).ellipse(a.box(cx - r, cy - r, cx + r, cy + r), outline=ACC_LO + (255,), width=max(1, int(a.r(r * .03))))


# ---------------------------------------------------------------- candidates

def cand1(a, layer):
    """ball 3: the ball fills the tile, a big navy italic 3 across it"""
    if layer in ('all', 'bg'):
        navy_bg(a)
    if layer in ('all', 'fg'):
        ball(a, .5, .5, .40, seam_w=.07, tilt=-28)
        f = font(HEAVY_I, a.r(.62))
        lay = a.layer()
        d = ImageDraw.Draw(lay)
        # navy 3 with a white rim, so it reads on the ball and the seam
        d.text((a.x(.5), a.x(.53)), '3', font=f, fill=NAVY + (255,), anchor='mm',
               stroke_width=int(a.r(.022)), stroke_fill=WHITE + (255,))
        a.img.alpha_composite(lay)


def cand2(a, layer):
    """headset: a VR headset whose front plate is a tennis ball"""
    if layer in ('all', 'bg'):
        navy_bg(a)
    if layer in ('all', 'fg'):
        d = ImageDraw.Draw(a.img)
        # strap, behind the headset
        d.rounded_rectangle(a.box(.02, .43, .98, .57), radius=a.r(.05), fill=FACE + (255,), outline=EDGE + (255,), width=int(a.r(.012)))
        # headset body
        x0, y0, x1, y1 = .08, .23, .92, .75
        sh = a.layer()
        ImageDraw.Draw(sh).rounded_rectangle(a.box(x0, y0 + .03, x1, y1 + .03), radius=a.r(.17), fill=(0, 0, 0, 160))
        a.img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(a.r(.02))))
        d.rounded_rectangle(a.box(x0, y0, x1, y1), radius=a.r(.17), fill=BODY + (255,), outline=EDGE + (255,), width=int(a.r(.012)))
        # front plate: tennis-ball felt with the seam
        px0, py0, px1, py1 = x0 + .03, y0 + .03, x1 - .03, y1 - .03
        plate = a.layer()
        pd = ImageDraw.Draw(plate)
        pd.rectangle(a.box(px0, py0, px1, py1), fill=ACCENT + (255,))
        hl = a.layer()
        ImageDraw.Draw(hl).ellipse(a.box(px0 - .05, py0 - .12, px1 - .2, py0 + .14), fill=ACC_HI + (150,))
        plate.alpha_composite(hl.filter(ImageFilter.GaussianBlur(a.r(.05))))
        sw = int(a.r(.032))
        for s in (-1, 1):
            ox = .5 + s * .53
            pd.ellipse(a.box(ox - .38, .49 - .42, ox + .38, .49 + .42), outline=WHITE + (255,), width=sw)
        m = a.mask()
        ImageDraw.Draw(m).rounded_rectangle(a.box(px0, py0, px1, py1), radius=a.r(.14), fill=255)
        a.put(plate, m)
        # nose cut-out at the bottom middle
        d.pieslice(a.box(.42, .64, .58, .82), 180, 360, fill=BODY + (255,))


def cand3(a, layer):
    """court: a blue court in perspective, white lines, a ball over the net"""
    if layer in ('all', 'bg'):
        navy_bg(a)
    if layer in ('all', 'fg'):
        d = ImageDraw.Draw(a.img)
        # court trapezoid: far baseline narrow, near baseline wide
        far_y, near_y = .42, .90
        fl, fr, nl, nr = .32, .68, .07, .93
        d.polygon(a.pts([(fl - .04, far_y - .02), (fr + .04, far_y - .02), (nr + .06, near_y + .04), (nl - .06, near_y + .04)]), fill=COURT_D + (255,))
        d.polygon(a.pts([(fl, far_y), (fr, far_y), (nr, near_y), (nl, near_y)]), fill=COURT + (255,))
        lw = int(a.r(.022))

        def lerp(p, q, t):
            return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
        FL, FR, NL, NR = (fl, far_y), (fr, far_y), (nl, near_y), (nr, near_y)
        L = lambda t: lerp(FL, NL, t)
        R = lambda t: lerp(FR, NR, t)
        for p, q in ((FL, FR), (NL, NR), (FL, NL), (FR, NR)):
            d.line(a.pts([p, q]), fill=WHITE + (255,), width=lw)
        # service lines and centre line (perspective: t not linear in y)
        tf, tn = .22, .70
        d.line(a.pts([L(tf), R(tf)]), fill=WHITE + (255,), width=lw)
        d.line(a.pts([L(tn), R(tn)]), fill=WHITE + (255,), width=lw)
        d.line(a.pts([lerp(L(tf), R(tf), .5), lerp(L(tn), R(tn), .5)]), fill=WHITE + (255,), width=lw)
        # net at t = .40
        tnet = .40
        nl_, nr_ = L(tnet), R(tnet)
        nh = .07
        d.polygon(a.pts([(nl_[0] - .03, nl_[1]), (nr_[0] + .03, nr_[1]), (nr_[0] + .03, nr_[1] - nh), (nl_[0] - .03, nl_[1] - nh)]), fill=(10, 16, 30, 230))
        d.line(a.pts([(nl_[0] - .03, nl_[1] - nh), (nr_[0] + .03, nr_[1] - nh)]), fill=WHITE + (255,), width=int(lw * 1.2))
        # ball over the net, with its shadow on the court
        sh = a.layer()
        ImageDraw.Draw(sh).ellipse(a.box(.47, .74, .63, .78), fill=(0, 0, 0, 120))
        a.img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(a.r(.01))))
        ball(a, .56, .27, .18, seam_w=.09, tilt=-20)


def cand4(a, layer):
    """racket: a racket head with a ball, diagonal"""
    if layer in ('all', 'bg'):
        navy_bg(a)
    if layer in ('all', 'fg'):
        lay = a.layer()
        d = ImageDraw.Draw(lay)
        cx, cy, rx, ry = .43, .40, .24, .30
        # handle and throat, drawn upright then rotated
        d.polygon(a.pts([(cx - .07, cy + ry - .02), (cx + .07, cy + ry - .02), (cx + .035, cy + ry + .15), (cx - .035, cy + ry + .15)]), fill=WHITE + (255,))
        d.rounded_rectangle(a.box(cx - .045, cy + ry + .12, cx + .045, cy + ry + .40), radius=a.r(.025), fill=COURT + (255,))
        d.rounded_rectangle(a.box(cx - .05, cy + ry + .38, cx + .05, cy + ry + .42), radius=a.r(.02), fill=WHITE + (255,))
        # strings: a coarse grid clipped to the head
        st = a.layer()
        sd = ImageDraw.Draw(st)
        sw = int(a.r(.012))
        n = 6
        for i in range(1, n):
            u = cx - rx + 2 * rx * i / n
            sd.line(a.pts([(u, cy - ry), (u, cy + ry)]), fill=(200, 214, 236, 255), width=sw)
        for i in range(1, 8):
            v = cy - ry + 2 * ry * i / 8
            sd.line(a.pts([(cx - rx, v), (cx + rx, v)]), fill=(200, 214, 236, 255), width=sw)
        m = a.mask()
        ImageDraw.Draw(m).ellipse(a.box(cx - rx, cy - ry, cx + rx, cy + ry), fill=255)
        st.putalpha(ImageChops.multiply(st.getchannel('A'), m))
        lay.alpha_composite(st)
        d.ellipse(a.box(cx - rx, cy - ry, cx + rx, cy + ry), outline=WHITE + (255,), width=int(a.r(.045)))
        lay = lay.rotate(35, center=(a.x(.5), a.x(.5)), resample=Image.BICUBIC)
        sh = Image.new('RGBA', lay.size, (0, 0, 0, 0))
        sh.putalpha(lay.getchannel('A').point(lambda v: v * 150 // 255))
        a.img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(a.r(.015))), (int(a.r(.012)), int(a.r(.02))))
        a.img.alpha_composite(lay)
        ball(a, .73, .70, .17, seam_w=.09, tilt=25)


# ------------------------------------------- VT3 in front of a ball (owner, 2026-11-12)
# "Simply VT3 with a tennis ball behind it - shaded in a similar way as the
# game": an arcade-style glossy look (gradient fills, a bevel, a white rim
# and a dark keyline round the letters, a soft drop shadow) drawn from
# scratch - fonts are the system's, no Sega lettering is traced or copied.

ORANGE = (240, 92, 24)
STEEL0, STEEL1 = (40, 74, 128), (8, 22, 58)          # the "3"'s deep blue gradient
PEARL0, PEARL1 = (255, 255, 255), (176, 186, 200)    # the letters' pearl / chrome


def vgrad(size, stops):
    """a vertical gradient image (RGBA) through the (t, colour) stops"""
    w, h = size
    col = Image.new('RGBA', (1, 256))
    for y in range(256):
        t = y / 255
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t0 <= t <= t1:
                u = (t - t0) / (t1 - t0) if t1 > t0 else 0
                col.putpixel((0, y), tuple(int(c0[i] + (c1[i] - c0[i]) * u) for i in range(3)) + (255,))
                break
    return col.resize((w, h), Image.BILINEAR)


def shifted(m, dx, dy):
    out = Image.new('L', m.size, 0)
    out.paste(m, (int(dx), int(dy)))
    return out


def glossy_ball(a, cx, cy, r, tilt=-24, gloss=0.0, rim=True):
    """a 3D tennis ball (art units): radial shading lit from the upper left,
    white seam arcs that follow the shading, a specular glint, a soft shadow"""
    S = a.S
    sh = a.layer()
    ImageDraw.Draw(sh).ellipse(a.box(cx - r * .92, cy - r * .80, cx + r * 1.06, cy + r * 1.16), fill=(0, 0, 0, 170))
    a.img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(a.r(r * .10))))
    lay = a.layer()
    # radial shading: a bright centre up-left fading to a dark limb
    rg = Image.radial_gradient('L').resize((int(a.r(r * 3.0)),) * 2, Image.BILINEAR)
    lit = Image.new('RGBA', rg.size, ACC_LO + (255,))
    hi = Image.new('RGBA', rg.size, (236, 252, 120, 255))
    lit = Image.composite(lit, hi, rg.point(lambda v: min(255, int(v * 1.25))))
    ox, oy = a.x(cx - r * .38) - rg.size[0] / 2, a.x(cy - r * .42) - rg.size[1] / 2
    lay.alpha_composite(lit, (int(ox), int(oy)))
    # limb darkening on the lower right
    dk = a.layer()
    ImageDraw.Draw(dk).ellipse(a.box(cx - r * .2, cy - r * .1, cx + r * 1.5, cy + r * 1.6), fill=(70, 96, 10, 150))
    lay.alpha_composite(dk.filter(ImageFilter.GaussianBlur(a.r(r * .35))))
    # seam
    seam = a.layer()
    sd = ImageDraw.Draw(seam)
    w = max(2, int(a.r(r * .075)))
    for s in (-1, 1):
        o = cx + s * r * 1.30
        sd.ellipse(a.box(o - r, cy - r * 1.08, o + r, cy + r * 1.08), outline=(250, 252, 240, 255), width=w)
    seam = seam.rotate(tilt, center=(a.x(cx), a.x(cy)), resample=Image.BICUBIC)
    # the seam darkens with the ball towards the lower right
    sdk = a.layer()
    ImageDraw.Draw(sdk).ellipse(a.box(cx - r * .1, cy - r * .1, cx + r * 1.4, cy + r * 1.4), fill=(90, 110, 40, 120))
    sdk = sdk.filter(ImageFilter.GaussianBlur(a.r(r * .3)))
    sdk.putalpha(ImageChops.multiply(sdk.getchannel('A'), seam.getchannel('A')))
    lay.alpha_composite(seam)
    lay.alpha_composite(sdk)
    # specular glint and a soft sheen band
    if gloss:
        g = a.layer()
        ImageDraw.Draw(g).ellipse(a.box(cx - r * .62, cy - r * .74, cx - r * .12, cy - r * .36), fill=(255, 255, 255, int(200 * gloss)))
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(a.r(r * .09))))
    m = a.mask()
    ImageDraw.Draw(m).ellipse(a.box(cx - r, cy - r, cx + r, cy + r), fill=255)
    a.put(lay, m)
    if rim:
        ImageDraw.Draw(a.img).ellipse(a.box(cx - r, cy - r, cx + r, cy + r), outline=(70, 92, 14, 255), width=max(1, int(a.r(r * .025))))


def close_mask(m, r):
    """morphological closing (dilate, then erode by about r px) of a mask, by
    blur-and-threshold: fills pockets and gaps narrower than ~2r, keeps the
    outer contour"""
    r = max(1, int(r))
    d = m.filter(ImageFilter.GaussianBlur(r * .5)).point(lambda v: 255 if v > 10 else 0)
    e = d.filter(ImageFilter.GaussianBlur(r * .5)).point(lambda v: 255 if v > 245 else 0)
    return ImageChops.lighter(e, m).filter(ImageFilter.GaussianBlur(1))


def text_mask(a, s, f, at, anchor='mm', stroke=0):
    m = a.mask()
    ImageDraw.Draw(m).text(at, s, font=f, fill=255, anchor=anchor, stroke_width=int(stroke), stroke_fill=255)
    return m


def fill(a, mask, img):
    lay = img.copy()
    lay.putalpha(ImageChops.multiply(img.getchannel('A'), mask))
    a.img.alpha_composite(lay)


def bevel(a, mask, depth, hi=150, lo=110):
    """an embossed edge: light on the upper left, dark on the lower right"""
    d = max(1, int(depth))
    top = ImageChops.subtract(mask, shifted(mask, d, d))
    bot = ImageChops.subtract(mask, shifted(mask, -d, -d))
    for m, c, al in ((top, (255, 255, 255), hi), (bot, (0, 10, 40), lo)):
        lay = Image.new('RGBA', a.img.size, c + (0,))
        lay.putalpha(m.filter(ImageFilter.GaussianBlur(d * .6)).point(lambda v: v * al // 255))
        lay.putalpha(ImageChops.multiply(lay.getchannel('A'), mask))
        a.img.alpha_composite(lay)


def vt3_letters(a, style):
    """bold italic VT3 across the lower part of the tile. style: 'chrome'
    (pearl VT, a deep blue 3, black keyline, white rim), 'lime' (white to
    lime letters, navy keyline) or 'orange' (white to orange letters, navy
    keyline, white rim)"""
    f = font(HEAVY_I, a.r(.42))
    # centred on (.505, .66): measured once, then drawn from the left baseline,
    # so "VT" alone lands exactly where it is in "VT3" (the 3 = the rest)
    probe = text_mask(a, 'VT3', f, (a.x(.5), a.x(.5)), anchor='ls').getbbox()
    at = (a.x(.5) + a.x(.505) - (probe[0] + probe[2]) / 2, a.x(.5) + a.x(.66) - (probe[1] + probe[3]) / 2)
    full = text_mask(a, 'VT3', f, at, anchor='ls')
    bb = full.getbbox()
    vt = text_mask(a, 'VT', f, at, anchor='ls').filter(ImageFilter.MaxFilter(5))
    rim_w, key_w = a.r(.042), a.r(.026)
    # the outlines are of the union of the letters, closed: the pockets and slivers
    # between touching glyphs (the T's bar over the 3's top arm, the 3's round
    # terminals) are filled, so no thin rim / dark hole runs through the word
    rim = close_mask(text_mask(a, 'VT3', f, at, anchor='ls', stroke=rim_w), a.r(.05))
    key = close_mask(text_mask(a, 'VT3', f, at, anchor='ls', stroke=key_w), a.r(.05))
    # soft drop shadow
    sh = Image.new('RGBA', a.img.size, (0, 0, 0, 0))
    sh.putalpha(shifted(rim, a.r(.012), a.r(.03)).filter(ImageFilter.GaussianBlur(a.r(.02))).point(lambda v: v * 200 // 255))
    a.img.alpha_composite(sh)
    rim_c = WHITE if style != 'lime' else (226, 236, 250)
    key_c = (6, 8, 16) if style == 'chrome' else (10, 22, 56)
    fill(a, rim, Image.new('RGBA', a.img.size, rim_c + (255,)))
    fill(a, key, Image.new('RGBA', a.img.size, key_c + (255,)))
    y0, y1 = int(bb[1]), int(bb[3])
    gsize = (a.S, y1 - y0)
    if style == 'chrome':
        body = Image.new('RGBA', a.img.size, (0, 0, 0, 0))
        body.paste(vgrad(gsize, [(0, PEARL0), (.42, (226, 232, 240)), (.50, PEARL1), (.62, (236, 240, 246)), (1, (200, 206, 216))]), (0, y0))
        three = Image.new('RGBA', a.img.size, (0, 0, 0, 0))
        three.paste(vgrad(gsize, [(0, (122, 170, 214)), (.35, STEEL0), (1, STEEL1)]), (0, y0))
        body = Image.composite(body, three, vt)
    elif style == 'lime':
        body = Image.new('RGBA', a.img.size, (0, 0, 0, 0))
        body.paste(vgrad(gsize, [(0, (255, 255, 255)), (.45, (240, 250, 200)), (.52, ACCENT), (1, (120, 156, 20))]), (0, y0))
    else:
        body = Image.new('RGBA', a.img.size, (0, 0, 0, 0))
        body.paste(vgrad(gsize, [(0, (255, 250, 236)), (.45, (255, 214, 150)), (.52, ORANGE), (1, (176, 52, 8))]), (0, y0))
    fill(a, full, body)
    bevel(a, full, a.r(.010))
    # a gloss line across the upper half of the letters
    gl = a.mask()
    ImageDraw.Draw(gl).rectangle([0, y0 + (y1 - y0) * .08, a.S, y0 + (y1 - y0) * .30], fill=90)
    gl = ImageChops.multiply(gl.filter(ImageFilter.GaussianBlur(a.r(.01))), full)
    lay = Image.new('RGBA', a.img.size, (255, 255, 255, 0))
    lay.putalpha(gl)
    a.img.alpha_composite(lay)


def vt3_bg(a, kind):
    if kind == 'navy':
        navy_bg(a)
        return
    # 'court': the court's blue with a light centre, as the game's menus
    d = ImageDraw.Draw(a.img)
    for y in range(a.S):
        t = y / a.S
        c = tuple(int(COURT[i] * (1 - t) + COURT_D[i] * t * .9) for i in range(3))
        d.line([(0, y), (a.S, y)], fill=c + (255,))
    g = a.layer()
    ImageDraw.Draw(g).ellipse([a.S * .05, a.S * .0, a.S * .95, a.S * .8], fill=(120, 170, 230, 110))
    a.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(a.S * .1)))


def cand5(a, layer):
    """VT3 chrome: pearl VT and a deep blue 3 with a black keyline and a
    white rim, in front of a glossy ball, on navy (the recommended one)"""
    if layer in ('all', 'bg'):
        vt3_bg(a, 'navy')
    if layer in ('all', 'fg'):
        glossy_ball(a, .56, .36, .30)
        vt3_letters(a, 'chrome')


def cand6(a, layer):
    """VT3 lime: white-to-lime letters with a navy keyline in front of the
    ball, on navy"""
    if layer in ('all', 'bg'):
        vt3_bg(a, 'navy')
    if layer in ('all', 'fg'):
        glossy_ball(a, .56, .36, .30)
        vt3_letters(a, 'lime')


def cand7(a, layer):
    """VT3 orange: white-to-orange letters on the court's blue, the ball
    behind"""
    if layer in ('all', 'bg'):
        vt3_bg(a, 'court')
    if layer in ('all', 'fg'):
        glossy_ball(a, .56, .36, .30)
        vt3_letters(a, 'orange')


CANDS = {1: cand1, 2: cand2, 3: cand3, 4: cand4, 5: cand5, 6: cand6, 7: cand7}
NAMES = {1: 'ball 3', 2: 'headset', 3: 'court', 4: 'racket', 5: 'VT3 chrome', 6: 'VT3 lime', 7: 'VT3 orange'}
DEFAULT = 7                      # installed (owner's pick 2026-11-12: VT3 orange, no specular spot on the ball)
SAFE = 66 / 108


def render(n, size, layer='all', k=1.0):
    a = Art(size * SS, k)
    CANDS[n](a, layer)
    return a.img.resize((size, size), Image.LANCZOS)


def write_set(n, out):
    os.makedirs(out, exist_ok=True)
    master = render(n, 1024)
    master.save(os.path.join(out, 'icon_1024.png'))
    for dname, px in DENS.items():
        p = os.path.join(out, f'drawable-{dname}')
        os.makedirs(p, exist_ok=True)
        # downscale from a 4x render, so every size is antialiased the same way
        render(n, px * 4).resize((px, px), Image.LANCZOS).save(os.path.join(p, 'ic_launcher.png'))
    ad = os.path.join(out, 'adaptive')
    os.makedirs(ad, exist_ok=True)
    # the legacy art fits in ~84 % of the tile; scale it into the 66 dp safe zone
    render(n, 432, 'fg', SAFE / .84).save(os.path.join(ad, 'ic_launcher_foreground.png'))
    render(n, 432, 'bg').save(os.path.join(ad, 'ic_launcher_background.png'))
    return master


def install(n):
    res = os.path.join(REPO, 'quest', 'vt3', 'src', 'main', 'res')
    for dname, px in DENS.items():
        p = os.path.join(res, f'drawable-{dname}', 'ic_launcher.png')
        render(n, px * 4).resize((px, px), Image.LANCZOS).save(p, optimize=True)
        print('wrote', os.path.relpath(p, REPO))


def masked(img, kind, bg):
    s = img.size[0]
    m = Image.new('L', (s * 4, s * 4), 0)
    d = ImageDraw.Draw(m)
    if kind == 'square':
        d.rectangle([0, 0, s * 4, s * 4], fill=255)
    elif kind == 'rounded':
        d.rounded_rectangle([0, 0, s * 4 - 1, s * 4 - 1], radius=s * 4 * .22, fill=255)
    else:
        d.ellipse([0, 0, s * 4 - 1, s * 4 - 1], fill=255)
    m = m.resize((s, s), Image.LANCZOS)
    out = Image.new('RGBA', (s, s), bg + (255,))
    out.paste(img, (0, 0), ImageChops.multiply(img.getchannel('A'), m))
    return out


def sheet(path, cands=None, sizes=(512, 192, 96, 48)):
    cands = list(cands or CANDS)
    sizes = list(sizes)
    big = sizes[0]
    pad = 16
    masks = ['square', 'rounded', 'circle']
    bgs = [(24, 24, 28), (236, 236, 240)]
    lab = font(LABEL, 28)
    row_w = sum(sizes) + pad * (len(sizes) + 1)
    # one row per (candidate, background, mask)
    rows = [(n, bg, mk) for n in cands for bg in bgs for mk in masks]
    col_w = row_w
    H = len(rows) // 2 * (big + pad) + pad + 60 * len(cands)
    W = col_w * 2 + 240
    S = Image.new('RGBA', (W, H), (60, 60, 66, 255))
    d = ImageDraw.Draw(S)
    y = pad
    for n in cands:
        master = render(n, 1024)
        d.text((pad, y + 10), f'Candidate {n}: {NAMES[n]}', font=lab, fill=(255, 255, 255, 255))
        y += 60
        for mk in masks:
            x = pad
            for bg in bgs:
                tile = Image.new('RGBA', (row_w, big + pad), bg + (255,))
                tx = pad
                for sz in sizes:
                    im = master.resize((sz, sz), Image.LANCZOS)
                    tile.alpha_composite(masked(im, mk, bg), (tx, (big - sz) // 2 + pad // 2))
                    tx += sz + pad
                S.alpha_composite(tile, (x, y))
                x += row_w + 16
            d.text((x + 8, y + big // 2 - 16), mk, font=lab, fill=(255, 255, 255, 255))
            y += big + pad
    S = S.crop((0, 0, W, y + pad))
    S.convert('RGB').save(path)
    return S


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--candidate', type=int, choices=sorted(CANDS), default=DEFAULT)
    ap.add_argument('--out', help='directory for the master, the densities and the adaptive layers')
    ap.add_argument('--install', action='store_true', help='write the legacy PNGs into quest/vt3/src/main/res')
    ap.add_argument('--sheet', help='write a contact sheet of every candidate to this PNG')
    ap.add_argument('--sheet-of', help='only these candidates on the sheet, e.g. 5,6,7')
    ap.add_argument('--sheet-sizes', default='512,192,96,48', help='the sheet\'s sizes, largest first')
    o = ap.parse_args()
    if not (o.out or o.install or o.sheet):
        ap.error('nothing to do: give --out, --install or --sheet')
    if o.sheet:
        sheet(o.sheet, [int(n) for n in o.sheet_of.split(',')] if o.sheet_of else None,
              [int(n) for n in o.sheet_sizes.split(',')])
        print('wrote', o.sheet)
    if o.out:
        write_set(o.candidate, o.out)
        print('wrote', o.out)
    if o.install:
        install(o.candidate)


if __name__ == '__main__':
    main()
