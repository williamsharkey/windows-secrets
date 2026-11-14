"""The two instruments the packs are for, named in one place. The 3.11 edition is SNDWAVE2000 by Algorithmic
Industries (fictional; brand kit in design/brand/sndwave2000/, strings in COPY.md); the XP edition is BASILISK SYNTH.
Persona texts may write {sw} and {xp} for these names."""
import os

SW = 'SNDWAVE2000'                 # the 3.11 edition (was BASILISK 16)
SW_MAKER = 'Algorithmic Industries'
XP = 'BASILISK SYNTH'              # the XP edition
SW_SHORT = 'SW2000'                # for tight table marks
BRAND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..', '..', '..', 'design', 'brand', 'sndwave2000')
BRAND_DIR = os.path.normpath(BRAND_DIR)
INK, PAPER, RED, ROSE = '#141414', '#f6f3ea', '#8a1c1c', '#d9b8b0'      # palette/sndwave2000.gpl
FONT_SERIF_BOLD = os.path.join(BRAND_DIR, 'fonts', 'DejaVuSerif-Bold.ttf')
FONT_SANS = os.path.join(BRAND_DIR, 'fonts', 'DejaVuSans.ttf')
FONT_SANS_BOLD = os.path.join(BRAND_DIR, 'fonts', 'DejaVuSans-Bold.ttf')
COMPANY_CAPS = 'ALGORITHMIC INDUSTRIES'                                 # COPY.md: capitals, wide letter spacing


def gridsun(max_px):
    """The largest Grid Sun mark (mark/gridsun-<n>.png) that fits in max_px, or None."""
    for n in (256, 64, 48, 32, 16):
        f = os.path.join(BRAND_DIR, 'mark', 'gridsun-%d.png' % n)
        if n <= max_px and os.path.exists(f):
            return f
    return None


# the compatibility badge (a period logo-programme sticker), in the brand's Technical Book: Stripe look
BADGE = {'top': 'DESIGNED FOR', 'name': SW, 'by': COMPANY_CAPS, 'bg': PAPER, 'ink': INK, 'accent': RED, 'rose': ROSE, 'frame': INK}
