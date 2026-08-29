// Renders assets/anim/hi-aaron.html (an animejs animation) frame by frame with
// Puppeteer and encodes the frames into assets/hi-aaron.gif.
//
// Run: node scripts/generate_hi_gif.js
"use strict";

const path = require("path");
const fs = require("fs");
const puppeteer = require("puppeteer");
const { PNG } = require("pngjs");
const { GIFEncoder, quantize, applyPalette } = require("gifenc");

const HTML_PATH = path.join(__dirname, "..", "assets", "anim", "hi-aaron.html");
const OUT_GIF = path.join(__dirname, "..", "assets", "hi-aaron.gif");

const WIDTH = 1200;
const HEIGHT = 300;
const FPS = 20;
const FRAME_MS = 1000 / FPS;

async function main() {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: WIDTH, height: HEIGHT });
  await page.goto("file://" + HTML_PATH.replace(/\\/g, "/"));

  const totalDuration = await page.evaluate(() => window.__totalDuration);
  const frameCount = Math.ceil(totalDuration / FRAME_MS);

  const gif = GIFEncoder();

  for (let i = 0; i < frameCount; i++) {
    const t = i * FRAME_MS;
    await page.evaluate((t) => window.__seek(t), t);
    const buf = await page.screenshot({ type: "png" });
    const png = PNG.sync.read(buf);
    const rgba = new Uint8Array(png.data.buffer, png.data.byteOffset, png.data.byteLength);

    const palette = quantize(rgba, 64);
    const index = applyPalette(rgba, palette);

    gif.writeFrame(index, WIDTH, HEIGHT, {
      palette,
      delay: FRAME_MS,
      repeat: 0,
    });

    if (i % 10 === 0) process.stdout.write(`frame ${i + 1}/${frameCount}\r`);
  }

  gif.finish();
  fs.writeFileSync(OUT_GIF, Buffer.from(gif.bytes()));
  console.log(`\nwrote ${OUT_GIF} (${frameCount} frames @ ${FPS}fps)`);

  await browser.close();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
