const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const dir = process.argv[2];
  const browser = await chromium.launch();
  for (const name of ['arquitectura', 'flujo']) {
    const svg = fs.readFileSync(`${dir}/${name}.svg`, 'utf8');
    const w = +svg.match(/width="(\d+)"/)[1], h = +svg.match(/height="(\d+)"/)[1];
    const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
    await page.setContent(`<html><body style="margin:0">${svg}</body></html>`);
    await page.screenshot({ path: `${dir}/${name}.png`, clip: { x: 0, y: 0, width: w, height: h } });
  }
  await browser.close();
})();
