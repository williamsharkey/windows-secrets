"""The two instruments the packs are for, named in one place. The 3.11 edition is SNDWAVE1993 by Algorithmic
Industries (brand kit in design/brand/sndwave1993/, strings in COPY.md; was SNDWAVE2000, before that BASILISK 16); the XP edition is BASILISK SYNTH.
Persona texts may write {sw} and {xp} for these names."""
import os

SW = 'SNDWAVE1993'                 # the 3.11 edition (was SNDWAVE2000, before that BASILISK 16)
SW_MAKER = 'Algorithmic Industries'
XP = 'BASILISK SYNTH'              # the XP edition
SW_SHORT = 'SW1993'                # for tight table marks
_BRAND_BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', '..', '..', '..', 'design', 'brand', '')
BRAND_DIR = next((os.path.join(_BRAND_BASE, k) for k in ('sndwave1993', 'sndwave2000') if os.path.isdir(os.path.join(_BRAND_BASE, k))), os.path.join(_BRAND_BASE, 'sndwave1993'))
BRAND_DIR = os.path.normpath(BRAND_DIR)
INK, PAPER, RED, ROSE = '#141414', '#f6f3ea', '#8a1c1c', '#d9b8b0'      # palette (brand kit); replaced from the kit's .gpl when it differs
def _kit(*parts):
    """A brand-kit file from the newest kit that has it (sndwave1993, then sndwave2000)."""
    for k in ('sndwave1993', 'sndwave2000'):
        f = os.path.normpath(os.path.join(_BRAND_BASE, k, *parts))
        if os.path.exists(f):
            return f
    return os.path.normpath(os.path.join(BRAND_DIR, *parts))


FONT_SERIF_BOLD = _kit('fonts', 'DejaVuSerif-Bold.ttf')
FONT_SANS = _kit('fonts', 'DejaVuSans.ttf')
FONT_SANS_BOLD = _kit('fonts', 'DejaVuSans-Bold.ttf')
COMPANY_CAPS = 'ALGORITHMIC INDUSTRIES'                                 # COPY.md: capitals, wide letter spacing


def gridsun(max_px):
    """The largest Grid Sun mark (mark/gridsun-<n>.png) that fits in max_px, or None."""
    for n in (256, 64, 48, 32, 16):
        f = _kit('mark', 'gridsun-%d.png' % n)
        if n <= max_px and os.path.exists(f):
            return f
    return None


# the compatibility badge (a period logo-programme sticker), in the brand's Technical Book: Stripe look
BADGE = {'top': 'DESIGNED FOR', 'name': SW, 'by': COMPANY_CAPS, 'bg': PAPER, 'ink': INK, 'accent': RED, 'rose': ROSE, 'frame': INK}
