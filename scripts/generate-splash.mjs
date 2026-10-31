#!/usr/bin/env node
/**
 * Generate iOS PWA splash screen PNGs — solid dark background (#1C1A17).
 * Pure Node.js, no dependencies. iOS shows the manifest icon on top.
 *
 * Usage: node scripts/generate-splash.mjs
 * Output: frontend/public/splash-*.png
 */

import { deflateSync } from 'node:zlib';
import { writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT_DIR = join(__dirname, '..', 'frontend', 'public');

// void --news dark background: #1C1A17
const BG = { r: 0x1C, g: 0x1A, b: 0x17 };

// iPhone splash sizes: [physical width, physical height, logical width, logical height, dpr]
const DEVICES = [
  // iPhone 15 Pro Max / 14 Pro Max
  [1290, 2796, 430, 932, 3],
  // iPhone 15 Pro / 14 Pro
  [1179, 2556, 393, 852, 3],
  // iPhone 14 / 13 / 12
  [1170, 2532, 390, 844, 3],
  // iPhone 14 Plus / 13 Pro Max / 12 Pro Max
  [1284, 2778, 428, 926, 3],
  // iPhone 11 / XR
  [828, 1792, 414, 896, 2],
  // iPhone X / XS / 11 Pro
  [1125, 2436, 375, 812, 3],
  // iPhone 8 / SE (3rd gen)
  [750, 1334, 375, 667, 2],
];

/* ---- CRC32 (PNG requires it for chunk checksums) ---- */
const crcTable = new Uint32Array(256);
for (let n = 0; n < 256; n++) {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
  crcTable[n] = c;
}
function crc32(buf) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < buf.length; i++) crc = crcTable[(crc ^ buf[i]) & 0xFF] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

/* ---- PNG chunk builder ---- */
function chunk(type, data) {
  const typeBytes = Buffer.from(type, 'ascii');
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const payload = Buffer.concat([typeBytes, data]);
  const crcBuf = Buffer.alloc(4);
  crcBuf.writeUInt32BE(crc32(payload));
  return Buffer.concat([len, payload, crcBuf]);
}

/* ---- Minimal PNG: indexed color, 1-entry palette ---- */
function solidPNG(width, height, r, g, b) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  // IHDR: indexed color (type 3), bit depth 1
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(width, 0);
  ihdr.writeUInt32BE(height, 4);
  ihdr[8] = 1;  // bit depth (1 bit — only 1 palette entry needed)
  ihdr[9] = 3;  // color type: indexed
  // compression, filter, interlace all 0

  // PLTE: single RGB entry
  const plte = Buffer.from([r, g, b]);

  // IDAT: each row = filter byte (0) + ceil(width/8) bytes of index 0
  const rowBytes = Math.ceil(width / 8);
  const rowSize = 1 + rowBytes;
  const raw = Buffer.alloc(rowSize * height); // all zeros = filter 0 + index 0

  const compressed = deflateSync(raw, { level: 9 });

  return Buffer.concat([
    sig,
    chunk('IHDR', ihdr),
    chunk('PLTE', plte),
    chunk('IDAT', compressed),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

/* ---- Generate all splash screens ---- */
let totalBytes = 0;

for (const [pw, ph, lw, lh, dpr] of DEVICES) {
  const name = `splash-${lw}x${lh}.png`;
  const png = solidPNG(pw, ph, BG.r, BG.g, BG.b);
  const path = join(OUT_DIR, name);
  writeFileSync(path, png);
  totalBytes += png.length;
  console.log(`  ${name}  ${pw}×${ph} @${dpr}x  (${(png.length / 1024).toFixed(1)} KB)`);
}

console.log(`\n  Total: ${DEVICES.length} splash screens, ${(totalBytes / 1024).toFixed(1)} KB`);
