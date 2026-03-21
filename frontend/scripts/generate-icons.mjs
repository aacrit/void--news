/**
 * generate-icons.mjs — Generate PNG favicon set from SVG source
 *
 * Uses sharp (bundled with Next.js) to convert SVG icons to PNG
 * at standard favicon sizes: 16, 32, 180, 192, 512.
 * Also creates a composite favicon.ico (16+32).
 *
 * Run: node scripts/generate-icons.mjs
 */

import sharp from "sharp";
import { readFileSync, writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = join(__dirname, "..", "public");

// ---- SVG sources for each icon context ----

// Favicon 16px — simplified mark (void circle + beam, no ticks)
const favicon16Svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="none" stroke="#1A1A1A" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="8" cy="7" r="5"/>
  <line x1="1.5" y1="7" x2="14.5" y2="7"/>
  <line x1="8" y1="12" x2="8" y2="14.5"/>
  <line x1="5.5" y1="14.5" x2="10.5" y2="14.5"/>
</svg>`;

// Favicon 32px — full mark
const favicon32Svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" fill="none" stroke="#1A1A1A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <circle cx="16" cy="13" r="9"/>
  <line x1="3" y1="13" x2="29" y2="13"/>
  <line x1="5" y1="11" x2="5" y2="15"/>
  <line x1="27" y1="11" x2="27" y2="15"/>
  <line x1="16" y1="22" x2="16" y2="29"/>
  <line x1="12" y1="29" x2="20" y2="29"/>
</svg>`;

// Apple touch icon (180px) — warm paper bg, dark mark
function makeSolidBgSvg(size, bgColor, strokeColor, strokeWidth) {
  const scale = size / 32;
  const iconSize = size * 0.6;
  const offset = (size - iconSize) / 2;
  const sw = strokeWidth;
  const r = 9 * (iconSize / 32);
  const cx = iconSize / 2;
  const cy = 13 * (iconSize / 32);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" fill="none" stroke-linecap="round" stroke-linejoin="round">
  <rect width="${size}" height="${size}" fill="${bgColor}"/>
  <g transform="translate(${offset}, ${offset * 0.85})" stroke="${strokeColor}" stroke-width="${sw}">
    <circle cx="${cx}" cy="${cy}" r="${r}"/>
    <line x1="${3 * iconSize / 32}" y1="${cy}" x2="${29 * iconSize / 32}" y2="${cy}"/>
    <line x1="${5 * iconSize / 32}" y1="${11 * iconSize / 32}" x2="${5 * iconSize / 32}" y2="${15 * iconSize / 32}"/>
    <line x1="${27 * iconSize / 32}" y1="${11 * iconSize / 32}" x2="${27 * iconSize / 32}" y2="${15 * iconSize / 32}"/>
    <line x1="${cx}" y1="${22 * iconSize / 32}" x2="${cx}" y2="${29 * iconSize / 32}"/>
    <line x1="${12 * iconSize / 32}" y1="${29 * iconSize / 32}" x2="${20 * iconSize / 32}" y2="${29 * iconSize / 32}"/>
  </g>
</svg>`;
}

async function generatePng(svgBuffer, size, outputName) {
  const png = await sharp(svgBuffer)
    .resize(size, size)
    .png()
    .toBuffer();
  const outputPath = join(publicDir, outputName);
  writeFileSync(outputPath, png);
  console.log(`  Created ${outputName} (${png.length} bytes)`);
  return png;
}

async function generateIco(png16, png32, outputName) {
  // ICO format: header + entries + image data
  // Simple ICO with 16x16 and 32x32 PNG entries
  const images = [
    { size: 16, data: png16 },
    { size: 32, data: png32 },
  ];

  const headerSize = 6;
  const entrySize = 16;
  const numImages = images.length;
  let dataOffset = headerSize + entrySize * numImages;

  // ICO header
  const header = Buffer.alloc(headerSize);
  header.writeUInt16LE(0, 0);     // Reserved
  header.writeUInt16LE(1, 2);     // Type: 1 = ICO
  header.writeUInt16LE(numImages, 4);

  const entries = [];
  const dataBuffers = [];

  for (const img of images) {
    const entry = Buffer.alloc(entrySize);
    entry.writeUInt8(img.size === 256 ? 0 : img.size, 0);  // Width
    entry.writeUInt8(img.size === 256 ? 0 : img.size, 1);  // Height
    entry.writeUInt8(0, 2);       // Color palette
    entry.writeUInt8(0, 3);       // Reserved
    entry.writeUInt16LE(1, 4);    // Color planes
    entry.writeUInt16LE(32, 6);   // Bits per pixel
    entry.writeUInt32LE(img.data.length, 8);  // Data size
    entry.writeUInt32LE(dataOffset, 12);      // Data offset
    entries.push(entry);
    dataBuffers.push(img.data);
    dataOffset += img.data.length;
  }

  const ico = Buffer.concat([header, ...entries, ...dataBuffers]);
  const outputPath = join(publicDir, outputName);
  writeFileSync(outputPath, ico);
  console.log(`  Created ${outputName} (${ico.length} bytes)`);
}

async function main() {
  console.log("Generating void --news favicon set...\n");

  // 1. Transparent 16x16 PNG (for favicon.ico)
  const png16 = await generatePng(
    Buffer.from(favicon16Svg),
    16,
    "favicon-16.png"
  );

  // 2. Transparent 32x32 PNG (for favicon.ico)
  const png32 = await generatePng(
    Buffer.from(favicon32Svg),
    32,
    "favicon-32.png"
  );

  // 3. favicon.ico (16 + 32)
  await generateIco(png16, png32, "favicon.ico");

  // 4. Apple touch icon — 180x180 with warm paper bg
  const apple180Svg = makeSolidBgSvg(180, "#FAF8F5", "#1A1A1A", 4);
  await generatePng(Buffer.from(apple180Svg), 180, "apple-touch-icon.png");

  // 5. PWA icon 192x192 — dark walnut bg, cream icon
  const pwa192Svg = makeSolidBgSvg(192, "#1C1A17", "#EDE8E0", 4.5);
  await generatePng(Buffer.from(pwa192Svg), 192, "icon-192.png");

  // 6. PWA icon 512x512 — dark walnut bg, cream icon
  const pwa512Svg = makeSolidBgSvg(512, "#1C1A17", "#EDE8E0", 8);
  await generatePng(Buffer.from(pwa512Svg), 512, "icon-512.png");

  console.log("\nFavicon set complete.");
}

main().catch(console.error);
