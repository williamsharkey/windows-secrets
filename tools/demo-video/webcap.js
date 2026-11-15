// The web edition, captured for the tour: williamsharkey.com/sndwave1993/play/ in headless Chromium (playwright-core),
// a 1920x1080 page recorded to video, plus screenshots. Usage: node webcap.js OUTDIR [URL]
const { chromium } = require(process.env.PW || 'playwright-core');
(async () => {
  const out = process.argv[2], url = process.argv[3] || 'https://williamsharkey.com/sndwave1993/play/';
  const browser = await chromium.launch({ executablePath: process.env.CHROME, args: ['--autoplay-policy=no-user-gesture-required'] });
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1,
                                         recordVideo: { dir: out, size: { width: 1920, height: 1080 } } });
  const page = await ctx.newPage();
  await page.goto(url, { waitUntil: 'networkidle', timeout: 120000 });
  await page.screenshot({ path: out + '/page.png' });
  const t0 = Date.now(), log = (m) => console.log(((Date.now() - t0) / 1000).toFixed(1), m);
  await page.click('button.b16go'); log('go');
  for (let k = 0; k < 40; k++) { await page.waitForTimeout(1000); if (k % 5 === 4) await page.screenshot({ path: `${out}/s${k + 1}.png` }); }
  // play a few notes with the computer keys (a s d f g)
  for (const key of ['a', 'd', 'g', 'j', 'g', 'd', 'a']) { await page.keyboard.down(key); await page.waitForTimeout(350); await page.keyboard.up(key); log('key ' + key); }
  await page.waitForTimeout(4000);
  await page.screenshot({ path: out + '/end.png' });
  await ctx.close(); await browser.close();
})();
