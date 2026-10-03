/* ---------------------------------------------------------------------------
   commonsImage: responsive widths for a Wikimedia Commons thumbnail.

   History stores each hero as the 1280px Commons thumbnail, and every card
   asked for that one size, so a phone showing a 319px card downloaded the same
   1280px file a 1440 desktop did, and more of them, because the vertical
   timeline lazy-loads further down: /history served 5.1 MB of images at 375
   against 3.7 MB at 1440 (audit 2 F7, P2-4).

   A Commons thumbnail URL carries its width (`/thumb/a/ab/Name.jpg/1280px-
   Name.jpg`), and the same path at another width is the same picture at that
   width. Only Wikimedia's standard thumbnail steps are offered (it throttles
   arbitrary widths), and only steps BELOW the stored one, since a thumbnail
   wider than its original is an error and the stored width is known to fit.
   Anything that is not a Commons thumbnail (an unscaled original, another
   host) gets no srcset and is left exactly as it was.
   --------------------------------------------------------------------------- */

const STEPS = [330, 500, 960, 1280] as const;
const THUMB = /^(https:\/\/(?:upload|thumb)\.wikimedia\.org\/wikipedia\/[^/]+\/thumb\/.+\/)(\d+)px-([^/?#]+)(\?[^#]*)?$/;
/* An unscaled original: `/wikipedia/commons/a/ab/Name.jpg`. Commons resolves
   a narrower original to the file itself, so 70 of the 170 History images
   were stored this way, and a phone downloaded the whole file (a 3461px
   photograph for a 319px card). Its thumbnails live at
   `/wikipedia/commons/thumb/a/ab/Name.jpg/500px-Name.jpg`, and only widths
   below the file's own exist, so the width must be known: the export carries
   it as `hero_image_width` from the Commons API. */
const ORIGINAL = /^(https:\/\/upload\.wikimedia\.org\/wikipedia\/[^/]+\/)([0-9a-f]\/[0-9a-f]{2})\/([^/?#]+)(\?[^#]*)?$/;
const RASTER = /\.(jpe?g|png|gif|webp)$/i;

/**
 * A srcset for a Commons image, or undefined when none can be offered.
 *
 * `originalWidth` is the file's own width. A thumbnail URL needs it only to
 * stay below the file; an unscaled original needs it to be offered at all.
 */
export function commonsSrcSet(
  url: string | null | undefined,
  originalWidth?: number | null,
): string | undefined {
  if (!url) return undefined;
  const max = typeof originalWidth === "number" && originalWidth > 0 ? originalWidth : Infinity;
  const m = url.match(THUMB);
  if (m) {
    const [, base, widthText, name, query = ""] = m;
    const stored = Number(widthText);
    if (!Number.isFinite(stored) || stored <= STEPS[0]) return undefined;
    const widths: number[] = STEPS.filter((w) => w < stored && w < max);
    widths.push(stored);
    return widths.map((w) => `${base}${w}px-${name}${query} ${w}w`).join(", ");
  }
  const o = url.match(ORIGINAL);
  if (!o || max === Infinity) return undefined;
  const [, root, hash, name] = o;
  if (!RASTER.test(name)) return undefined;
  const widths = STEPS.filter((w) => w < max);
  if (!widths.length) return undefined;
  return [
    ...widths.map((w) => `${root}thumb/${hash}/${name}/${w}px-${name} ${w}w`),
    `${url} ${max}w`,
  ].join(", ");
}
