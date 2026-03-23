/* ===========================================================================
   void --news — Haptic Feedback System
   Tiered feedback: vibration on Android, AudioContext micro-clicks on iOS.

   Tiers:
     micro    — barely perceptible texture (filter chips, scroll boundaries)
     light    — acknowledges action (story tap, nav switch, toggles)
     medium   — confirms transition (panel open, audio play, theme swap)
     confirm  — deliberate measured action (refresh, edition change)

   Android: Vibration API patterns (3–50ms total).
   iOS/desktop: AudioContext sine-wave micro-clicks (1–4ms, inaudible-to-subtle).
   The audio fallback mimics Apple's own keyboard tap — a short sine burst
   shaped by a fast gain envelope so it reads as tactile, not musical.
   =========================================================================== */

const canVibrate =
  typeof navigator !== "undefined" && typeof navigator.vibrate === "function";

/* ---------------------------------------------------------------------------
   AudioContext tap engine — iOS/desktop fallback
   Creates a short sine-wave "click" through a fast gain envelope.
   Frequencies and durations tuned so micro is nearly inaudible and
   confirm is a soft, warm triple-tap. Reuses a single AudioContext
   (created on first interaction to satisfy autoplay policy).
   --------------------------------------------------------------------------- */

let _ctx: AudioContext | null = null;

function getAudioCtx(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (_ctx) return _ctx;
  try {
    _ctx = new (window.AudioContext || (window as /* eslint-disable-line @typescript-eslint/no-explicit-any */ any).webkitAudioContext)();
    return _ctx;
  } catch {
    return null;
  }
}

/**
 * Play a sine-wave micro-click.
 * @param freq  — Hz (higher = sharper click, lower = softer thud)
 * @param dur   — seconds (1-4ms typical)
 * @param gain  — volume 0-1 (keep ≤0.08 for subtle)
 * @param delay — seconds offset from now (for multi-tap patterns)
 */
function tap(freq: number, dur: number, gain: number, delay = 0) {
  const ctx = getAudioCtx();
  if (!ctx) return;
  // Resume suspended context (autoplay policy)
  if (ctx.state === "suspended") ctx.resume();

  const t = ctx.currentTime + delay;
  const osc = ctx.createOscillator();
  const env = ctx.createGain();

  osc.type = "sine";
  osc.frequency.value = freq;

  // Fast attack → instant decay envelope (reads as a click, not a tone)
  env.gain.setValueAtTime(0, t);
  env.gain.linearRampToValueAtTime(gain, t + 0.001); // 1ms attack
  env.gain.linearRampToValueAtTime(0, t + dur);       // decay to silence

  osc.connect(env);
  env.connect(ctx.destination);
  osc.start(t);
  osc.stop(t + dur + 0.01);
}

/* ---------------------------------------------------------------------------
   Tier implementations — vibrate on Android, audio-tap on iOS/desktop
   --------------------------------------------------------------------------- */

/** Micro — barely perceptible texture. Filter chips, scroll detents. */
export function hapticMicro() {
  if (canVibrate) {
    navigator.vibrate(6);
  } else {
    tap(4200, 0.002, 0.03);  // 4.2kHz, 2ms, very quiet
  }
}

/** Light — acknowledges action. Story card tap, read-more toggles. */
export function hapticLight() {
  if (canVibrate) {
    navigator.vibrate(10);
  } else {
    tap(3600, 0.003, 0.05);  // 3.6kHz, 3ms, soft click
  }
}

/** Medium — confirms transition. Panel open, audio play, theme toggle.
 *  Vibration: [12, 40, 8]ms double-tap. Audio: two taps 50ms apart. */
export function hapticMedium() {
  if (canVibrate) {
    navigator.vibrate([12, 40, 8]);
  } else {
    tap(3200, 0.003, 0.06);         // first tap
    tap(2800, 0.003, 0.04, 0.05);   // softer settle 50ms later
  }
}

/** Confirm — deliberate measured action. Refresh confirm, edition switch.
 *  Vibration: [10, 30, 15, 30, 8]ms three-stage.
 *  Audio: three descending taps — tap, hold, release. */
export function hapticConfirm() {
  if (canVibrate) {
    navigator.vibrate([10, 30, 15, 30, 8]);
  } else {
    tap(3400, 0.003, 0.06);          // tap
    tap(2600, 0.004, 0.05, 0.04);    // hold (lower, longer)
    tap(2200, 0.002, 0.03, 0.10);    // release (softest)
  }
}

/** Scroll boundary — ultra-subtle at overscroll edges. */
export function hapticScrollEdge() {
  if (canVibrate) {
    navigator.vibrate(4);
  } else {
    tap(4800, 0.0015, 0.02);  // highest freq, shortest, quietest
  }
}

/** Seek tick — feather-light detent for audio scrubbing. */
export function hapticTick() {
  if (canVibrate) {
    navigator.vibrate(3);
  } else {
    tap(5000, 0.001, 0.025);  // crisp tick
  }
}
