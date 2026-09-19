/* ===========================================================================
   void --news — Haptic Feedback System
   Tiered feedback: vibration on Android. Silent no-op elsewhere.

   Tiers:
     micro    — barely perceptible texture (filter chips, scroll boundaries)
     light    — acknowledges action (story tap, nav switch, toggles)
     medium   — confirms transition (panel open, audio play, theme swap)
     confirm  — deliberate measured action (refresh, edition change)

   Android: Vibration API patterns (3–50ms total).
   iOS/desktop: NO-OP (2026-08-11). The old AudioContext sine-click fallback
   emitted real, audible sound on every tap wherever vibration was
   unavailable — all of iOS Safari and every desktop — with no opt-in and no
   respect for quiet environments. Un-asked-for sound violates the editorial
   restraint of the product; haptics are now vibration-only.
   =========================================================================== */

const canVibrate =
  typeof navigator !== "undefined" && typeof navigator.vibrate === "function";

/* ---------------------------------------------------------------------------
   Tier implementations — vibrate on Android, silent elsewhere
   --------------------------------------------------------------------------- */

/** Micro — barely perceptible texture. Filter chips, scroll detents. */
export function hapticMicro() {
  if (canVibrate) navigator.vibrate(6);
}

/** Light — acknowledges action. Story card tap, read-more toggles. */
export function hapticLight() {
  if (canVibrate) navigator.vibrate(10);
}

/** Medium — confirms transition. Panel open, audio play, theme toggle.
 *  Vibration: [12, 40, 8]ms double-tap. */
export function hapticMedium() {
  if (canVibrate) navigator.vibrate([12, 40, 8]);
}

/** Confirm — deliberate measured action. Refresh confirm, edition switch.
 *  Vibration: [10, 30, 15, 30, 8]ms three-stage. */
export function hapticConfirm() {
  if (canVibrate) navigator.vibrate([10, 30, 15, 30, 8]);
}

/** Scroll boundary — ultra-subtle at overscroll edges. */
export function hapticScrollEdge() {
  if (canVibrate) navigator.vibrate(4);
}

/** Seek tick — feather-light detent for audio scrubbing. */
export function hapticTick() {
  if (canVibrate) navigator.vibrate(3);
}
