// node measure.cjs <project>/index.html <out.json>: the settled layout of every item of an overlay composition (frame pixels), from headless Chrome.
const { chromium } = require("playwright");
const fs = require("fs");
(async () => {
  const [, , page, out] = process.argv;
  const b = await chromium.launch({ args: ["--allow-file-access-from-files"] });
  const p = await b.newPage({ viewport: { width: 2560, height: 1440 } });
  await p.goto("file://" + page);
  await p.waitForFunction("window.__measure !== undefined");
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(300);
  const boxes = await p.evaluate(() => window.__measure());
  const timing = await p.evaluate(() => window.__timing());
  fs.writeFileSync(out, JSON.stringify({ boxes, timing }, null, 1));
  await b.close();
})();
