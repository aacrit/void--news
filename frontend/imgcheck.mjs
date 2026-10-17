import { chromium } from 'playwright';
const b = await chromium.launch({
  executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--ignore-certificate-errors'],
});
const ctx = await b.newContext({ viewport: { width: 1440, height: 1200 }, ignoreHTTPSErrors: true });
const p = await ctx.newPage();
for (const slug of ['apollo-11-moon-landing', 'chernobyl-disaster', 'french-revolution']) {
  await p.goto(`http://localhost:4175/history/${slug}/`, { waitUntil: 'networkidle', timeout: 60000 });
  await p.waitForTimeout(3500);
  const imgs = await p.$$eval('img', is => is.map(i => ({ ok: i.naturalWidth > 0, w: i.naturalWidth, src: (i.currentSrc||i.src).slice(0,60) })));
  const hero = await p.$eval('.hist-stage__hero', el => {
    const bg = getComputedStyle(el).backgroundImage;
    return bg.slice(0, 70);
  }).catch(() => '(none)');
  console.log(`${slug.padEnd(24)} imgs=${imgs.length} loaded=${imgs.filter(i=>i.ok).length} hero=${hero.includes('wikimedia')?'wikimedia':'?'}`);
  imgs.slice(0,2).forEach(i => console.log('    ', i.ok ? 'OK ' : 'FAIL', i.w, i.src));
}
await p.goto('http://localhost:4175/history/apollo-11-moon-landing/', { waitUntil: 'networkidle' });
await p.waitForTimeout(3500);
await p.screenshot({ path: '/tmp/hist-images.png', fullPage: false });
await b.close();
