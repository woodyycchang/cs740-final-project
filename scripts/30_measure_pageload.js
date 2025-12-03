#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

function iso(){ return new Date().toISOString(); }
function asInt(v){ return (Number.isFinite(v) && v >= 0) ? Math.round(v) : 'NA'; }
function pickChromePath(){
  const env = process.env.CHROME_PATH || process.env.PUPPETEER_EXECUTABLE_PATH;
  if (env && fs.existsSync(env)) return env;
  try { const p = puppeteer.executablePath?.(); if (p && fs.existsSync(p)) return p; } catch(_) {}
  const mac = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  return fs.existsSync(mac) ? mac : null;
}

(async () => {
  const site = process.argv[2] || 'example.com';
  const mode = process.argv[3] || 'public_udp';
  const out  = process.argv[4] || 'data/raw/web_smoke.csv';
if (!fs.existsSync(out)) fs.appendFileSync(out, "ts,mode,site,ttfb_ms,dom_ms,load_ms,status\n");
  const tmp  = process.argv[5] || fs.mkdtempSync('/tmp/pageload-');
  const url  = site.startsWith('http') ? site : `https://${site}`;

  fs.mkdirSync(path.dirname(out), { recursive: true });

  let browser, ctx, page;
  try {
    const exe = pickChromePath();
    const launch = {
      headless: 'new',
      args: [
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-features=AsyncDns',
        '--disable-features=DnsOverHttps',
        '--disable-quic',
        `--user-data-dir=${tmp}`
      ],
    };
    if (exe) launch.executablePath = exe;

    browser = await puppeteer.launch(launch);

    // Create a page in a way that works across Puppeteer versions
    if (typeof browser.createIncognitoBrowserContext === 'function') {
      ctx = await browser.createIncognitoBrowserContext();
      page = await ctx.newPage();
    } else if (typeof browser.createBrowserContext === 'function') {
      ctx = await browser.createBrowserContext();
      page = await ctx.newPage();
    } else if (typeof browser.newPage === 'function') {
      page = await browser.newPage();
    } else {
      throw new Error('No supported method to create a new page.');
    }

    page.setDefaultNavigationTimeout(45000);
    page.setDefaultTimeout(45000);

    await page.goto(url, { waitUntil: ['domcontentloaded', 'load'] });

    const m = await page.evaluate(() => {
      try {
        const nav = performance.getEntriesByType('navigation')[0];
        if (nav) {
          return { ttfb: nav.responseStart, dom: nav.domContentLoadedEventEnd, load: nav.loadEventEnd };
        }
        const t = performance.timing;
        return {
          ttfb: t.responseStart - t.navigationStart,
          dom:  t.domContentLoadedEventEnd - t.navigationStart,
          load: t.loadEventEnd - t.navigationStart
        };
      } catch {
        return { ttfb: NaN, dom: NaN, load: NaN };
      }
    });

    const row = [iso(), mode, site, asInt(m.ttfb), asInt(m.dom), asInt(m.load), 'ok'].join(',');
    fs.appendFileSync(out, row + '\n', 'utf8');

    if (ctx?.close) await ctx.close();
    await browser.close();
  } catch (e) {
    const row = [iso(), mode, site, 'NA', 'NA', 'NA', 'err'].join(',');
    fs.appendFileSync(out, row + '\n', 'utf8');
    try { if (ctx?.close) await ctx.close(); } catch {}
    try { if (browser) await browser.close(); } catch {}
    console.error('[pageload error]', e?.message || e);
    process.exitCode = 1;
  }
})();
