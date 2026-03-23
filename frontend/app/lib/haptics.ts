/* ===========================================================================
   void --news — Haptic Feedback System
   Tiered vibration patterns modeled after Apple Taptic Engine + Google Material.

   Tiers:
     micro    — barely perceptible texture (filter chips, scroll boundaries)
     light    — acknowledges action (story tap, nav switch, toggles)
     medium   — confirms transition (panel open, audio play, theme swap)
     confirm  — deliberate measured action (refresh, edition change)

   All calls are no-ops on devices without Vibration API (iOS Safari, desktop).
   Patterns are short enough to never feel intrusive — max 50ms total.
   =========================================================================== */

const canVibrate =
  typeof navigator !== "undefined" && typeof navigator.vibrate === "function";

/** Micro — 6ms pulse. Filter chips, minor selections, scroll detents. */
export function hapticMicro() {
  if (canVibrate) navigator.vibrate(6);
}

/** Light — 10ms pulse. Story card tap, navigation, read-more toggles. */
export function hapticLight() {
  if (canVibrate) navigator.vibrate(10);
}

/** Medium — double-tap pattern. Panel open, audio play, theme toggle.
 *  [12, 40, 8] = tap (12ms) + gap (40ms) + settle (8ms). */
export function hapticMedium() {
  if (canVibrate) navigator.vibrate([12, 40, 8]);
}

/** Confirm — deliberate three-stage. Refresh confirm, edition switch.
 *  [10, 30, 15, 30, 8] = tap + gap + hold + gap + release. */
export function hapticConfirm() {
  if (canVibrate) navigator.vibrate([10, 30, 15, 30, 8]);
}

/** Scroll boundary — ultra-subtle 4ms pulse at overscroll edges. */
export function hapticScrollEdge() {
  if (canVibrate) navigator.vibrate(4);
}

/** Seek tick — feather-light detent for audio scrubbing. */
export function hapticTick() {
  if (canVibrate) navigator.vibrate(3);
}
