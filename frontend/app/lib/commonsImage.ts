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

/** A srcset for a Commons thumbnail, or undefined for anything else. */
export function commonsSrcSet(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  const m = url.match(THUMB);
  if (!m) return undefined;
  const [, base, widthText, name, query = ""] = m;
  const stored = Number(widthText);
  if (!Number.isFinite(stored) || stored <= STEPS[0]) return undefined;
  const widths: number[] = STEPS.filter((w) => w < stored);
  widths.push(stored);
  return widths.map((w) => `${base}${w}px-${name}${query} ${w}w`).join(", ");
}
