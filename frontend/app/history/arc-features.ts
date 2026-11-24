/**
 * Arc Connection Feature Flags
 * Toggle any feature on/off and rebuild. All flags default to true.
 */
export const ARC_FEATURES = {
  /** Stage 5.5: Connection descriptions between Stage 5 and Stage 6 */
  THREAD_STAGE: true,
  /** Stage 6 rewrite: Connection-ranked next reads instead of chronological */
  DOSSIER: true,
  /** /history/threads route: Thematic thread strips across the full archive */
  LEDGER: true,
  /** EventDetail right sidebar: "Elsewhere, Meanwhile" parallel connections */
  SIDEBAR: true,
  /** HistoryLanding: Thread overlay mode on the organic ink timeline */
  LONG_VIEW: true,
} as const;
