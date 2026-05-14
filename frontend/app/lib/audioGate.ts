/**
 * Audio feature gate — single source of truth for whether void --onair
 * (audio brief / TTS / podcast / floating player) is exposed to users.
 *
 * Flip the kill switch via the NEXT_PUBLIC_DISABLE_AUDIO env var:
 *   NEXT_PUBLIC_DISABLE_AUDIO=1  →  ALL audio UI hidden, AudioProvider
 *                                   short-circuits, no requests for the
 *                                   .mp3 brief, no FloatingPlayer mount,
 *                                   no "void --onair" mentions.
 *   NEXT_PUBLIC_DISABLE_AUDIO=0  →  audio fully enabled (default).
 *
 * Pipeline has a matching DISABLE_AUDIO env gate (see audio_producer.py
 * and .github/workflows/pipeline.yml). Both flags are flipped together
 * to disable end-to-end; flipped back together to re-enable.
 *
 * See: CLAUDE.md → Parking Lot.
 */
export const AUDIO_DISABLED: boolean =
  (process.env.NEXT_PUBLIC_DISABLE_AUDIO ?? "1") === "1";

/** Convenience inverse — read-side. */
export const AUDIO_ENABLED: boolean = !AUDIO_DISABLED;
