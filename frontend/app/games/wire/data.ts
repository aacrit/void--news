/* ==========================================================================
   THE WIRE — Daily "Intercept the Transmission" Word Puzzle Data
   Each day: an evocative paragraph with 4 hidden words. Find the words,
   find the connection.
   ========================================================================== */

export interface WireChallenge {
  id: number;
  date: string;
  transmission: string; // paragraph with [WORD_A], [WORD_B], [WORD_C], [WORD_D] placeholders
  hidden_words: [string, string, string, string]; // exact words, uppercase
  connection: string; // what they share — shown on reveal
  connection_hint: string; // shown after 2 wrong connection guesses
  reveal: string; // 2-3 sentence commentary on the connection
}

export const WIRE_CHALLENGES: WireChallenge[] = [
  {
    id: 1,
    date: "2026-04-10",
    transmission:
      "She found the [WORD_A] in the back of the drawer, exactly where he said he'd left it.\nThe [WORD_B] broke just as the ceremony was about to start.\nThree months earlier, she'd made a [WORD_C] she wasn't sure she could keep.\nThe [WORD_D] of the vow hung in the air long after the room had emptied.",
    hidden_words: ["LETTER", "SILENCE", "PROMISE", "WEIGHT"],
    connection: "things that linger",
    connection_hint: "they stay after the moment passes",
    reveal:
      "Four words for the same phenomenon: the thing that remains after the event. None of them require a body. All of them require time.",
  },
  {
    id: 2,
    date: "2026-04-11",
    transmission:
      "The [WORD_A] arrived without a return address.\nBy noon, everyone in the building had heard the [WORD_B].\nShe left the [WORD_C] on the table and walked out without looking back.\nHe spent the rest of the week trying to decode the [WORD_D].",
    hidden_words: ["PACKAGE", "RUMOR", "NOTE", "SIGNAL"],
    connection: "things sent without a sender",
    connection_hint: "they travel without their origin",
    reveal:
      "Each word describes a transmission that has detached from its source. The message arrives. The messenger has already gone. This is the structure of most important information.",
  },
  {
    id: 3,
    date: "2026-04-12",
    transmission:
      "The [WORD_A] in the hallway had been wrong for three years.\nEveryone agreed the [WORD_B] needed fixing, but nobody called.\nShe ignored the [WORD_C] until it was too late to pretend she hadn't seen it.\nThe [WORD_D] was still ticking when they found the room empty.",
    hidden_words: ["CLOCK", "LEAK", "SIGN", "ALARM"],
    connection: "warnings that go unheeded",
    connection_hint: "they were right all along",
    reveal:
      "Four ways of saying: something was wrong, and we knew, and we waited. The clock, the leak, the sign, the alarm — each is a system designed to interrupt complacency. Each can be silenced.",
  },
  {
    id: 4,
    date: "2026-04-13",
    transmission:
      "He built his entire [WORD_A] on three things he later found out were false.\nThe [WORD_B] had seemed like such a good idea at the time.\nShe kept returning to the same [WORD_C], looking for the part she'd missed.\nThe [WORD_D] was elegant, complete, and completely wrong.",
    hidden_words: ["THEORY", "PLAN", "STORY", "ARGUMENT"],
    connection: "structures that collapse from inside",
    connection_hint: "they were perfect until they weren't",
    reveal:
      "The collapse of a theory, a plan, a story, an argument — each falls the same way: from a flaw present at the foundation. The elegance was always a sign something had been omitted.",
  },
  {
    id: 5,
    date: "2026-04-14",
    transmission:
      "The [WORD_A] was the last thing she packed.\nHe'd been carrying the [WORD_B] for so long he'd forgotten what it weighed.\nSomewhere in the archive was a [WORD_C] that explained everything.\nThe [WORD_D] would have to speak for itself now.",
    hidden_words: ["PHOTOGRAPH", "GUILT", "DOCUMENT", "WORK"],
    connection: "things left behind",
    connection_hint: "they outlast the person who made them",
    reveal:
      "Photograph, guilt, document, work — each persists after departure. Three of them were made intentionally. One was not. The archive keeps all four without preference.",
  },
];

export function getDailyWireChallenge(date?: string): WireChallenge {
  const d = date ? new Date(date + "T00:00:00") : new Date();
  const start = new Date(d.getFullYear(), 0, 0);
  const dayOfYear = Math.floor(
    (d.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)
  );
  return WIRE_CHALLENGES[(dayOfYear - 1) % WIRE_CHALLENGES.length];
}

export const DAILY_WIRE = getDailyWireChallenge();
