import sys, time, json
sys.path.insert(0, '/home/wm/pwlib')
from playwright.sync_api import sync_playwright
url = sys.argv[1]; out = sys.argv[2]
JS_MEASURE = r"""
async (ch) => {
  const c = document.querySelector('#screen canvas');
  const ctx = c.getContext('2d', {willReadFrequently: true});
  const sig = () => { const d = ctx.getImageData(8, 706, 840, 26).data; let h = 0; for (let i = 0; i < d.length; i += 4) h = (h * 31 + d[i] + d[i+1] * 3 + d[i+2] * 7) | 0; return h; };
  const before = sig();
  const t0 = performance.now();
  document.getElementById('stagebox').dispatchEvent(new KeyboardEvent('keydown', {key: ch, bubbles: true}));
  while (performance.now() - t0 < 3000) {
    await new Promise(r => requestAnimationFrame(r));
    if (sig() !== before) return performance.now() - t0;
  }
  return -1;
}
"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 1000})
    errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(url)
    time.sleep(4)
    pg.click('#start')
    t0 = time.time()
    while time.time() - t0 < 90:
        if 'You are driving' in pg.inner_text('#status'): break
        time.sleep(0.5)
    print('ready after %.1fs' % (time.time() - t0))
    pg.focus('#stagebox')
    time.sleep(1.5)
    lats = []
    for ch in 'what time is it':
        lats.append(pg.evaluate(JS_MEASURE, ch))
        time.sleep(0.15)
    print('keystroke->pixels ms:', [round(x) for x in lats])
    ok = sorted(x for x in lats if x > 0)
    if ok: print('median %.0f ms, p90 %.0f ms, min %.0f, max %.0f' % (ok[len(ok)//2], ok[int(len(ok)*.9)-1], ok[0], ok[-1]))
    pg.keyboard.press('Enter')
    time.sleep(14)
    pg.screenshot(path=out + '-after.png')
    print('status:', pg.inner_text('#status')[:200]); print('errors:', errs[:5])
    pg.click('#leave')
    time.sleep(1)
    b.close()
