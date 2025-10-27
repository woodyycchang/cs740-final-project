const fs = require('fs');
const puppeteer = require('puppeteer');

(async () => {
  const [site, mode, out, userDir] = process.argv.slice(2);
  if (!site || !mode || !out || !userDir) {
    console.error('usage: node scripts/30_measure_pageload.js <site> <mode> <out_csv> <userDataDir>');
    process.exit(2);
  }
  const browser = await puppeteer.launch({
    headless: 'new',
    userDataDir: userDir,
    args: ['--no-sandbox','--disable-background-networking']
  });
  const page = await browser.newPage();
  try {
    await page.goto('https://' + site, {waitUntil: 'load', timeout: 60000});
    const nav = await page.evaluate(() => performance.getEntriesByType('navigation')[0]);
    const rec = [
      new Date().toISOString(), mode, site,
      (nav.responseStart - nav.startTime).toFixed(2),
      (nav.domContentLoadedEventEnd - nav.startTime).toFixed(2),
      (nav.loadEventEnd - nav.startTime).toFixed(2),
      'ok'
    ].join(',');
    fs.appendFileSync(out, rec + '\n');
  } catch (e) {
    fs.appendFileSync(out, [new Date().toISOString(), mode, site, 'NA','NA','NA','err'].join(',')+'\n');
  }
  await browser.close();
})();
