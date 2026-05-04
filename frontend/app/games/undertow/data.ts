/* ==========================================================================
   UNDERTOW — Daily Cultural Subtext Puzzle Data
   30 daily challenges. Pipeline will rotate by day-of-year.
   All artifacts: no names, no dates, no sources. Just the text.
   ========================================================================== */

export type ArtifactCategory =
  | "advertising"
  | "speech"
  | "wellness"
  | "corporate"
  | "literary"
  | "lyric"
  | "linkedin"
  | "manifesto";

export interface Artifact {
  id: string;
  text: string;
  category: ArtifactCategory;
  axis_position: number; // -2 (left pole) to +2 (right pole)
  highlighted_words: string[];
  reveal: string; // 2-3 sentences, precise + occasionally wry
}

export interface Axis {
  label: string;
  left_pole: string;
  right_pole: string;
  description: string;
}

export interface DailyChallenge {
  id: number;
  date: string;
  axis: Axis;
  artifacts: Artifact[];
  correct_order: string[]; // ids ordered left pole → right pole
  tomorrow_axis?: string;
}

/** Category label colors — muted, atmospheric */
export const CATEGORY_COLORS: Record<ArtifactCategory, string> = {
  advertising: "#b5a08a",
  speech:      "#8a9bb5",
  wellness:    "#a08ab5",
  corporate:   "#8ab5a0",
  literary:    "#b5b08a",
  lyric:       "#b58a8a",
  linkedin:    "#8aabb5",
  manifesto:   "#b58aaa",
};

/** Background images per axis — Unsplash License (free commercial use) */
export const AXIS_IMAGES: Record<string, { url: string; credit: string }> = {
  CULT: {
    url: "https://images.unsplash.com/photo-XS49QQVKh_8?w=1920&q=80&auto=format&fit=crop",
    credit: "Ilia Bronskiy",
  },
  BOSS: {
    url: "https://images.unsplash.com/photo-AHlWf9ICfIc?w=1920&q=80&auto=format&fit=crop",
    credit: "Willian Justen de Vasconcellos",
  },
  "2AM": {
    url: "https://images.unsplash.com/photo-Xq1VNBrpJzI?w=1920&q=80&auto=format&fit=crop",
    credit: "Baris Cobanoglu",
  },
  DAD: {
    url: "https://images.unsplash.com/photo-7q-hhI27pUU?w=1920&q=80&auto=format&fit=crop",
    credit: "Hasan Almasi",
  },
  DEFAULT: {
    url: "https://images.unsplash.com/photo-f01ZbhYCBuQ?w=1920&q=80&auto=format&fit=crop",
    credit: "Alexander X.",
  },
};

export function getAxisImage(leftPole: string): { url: string; credit: string } {
  const key = Object.keys(AXIS_IMAGES).find((k) => leftPole.includes(k));
  return key ? AXIS_IMAGES[key] : AXIS_IMAGES["DEFAULT"];
}

/** Return today's challenge based on day-of-year (cycles through all 30) */
export function getDailyChallenge(date?: string): DailyChallenge {
  const d = date ? new Date(date + "T00:00:00") : new Date();
  const start = new Date(d.getFullYear(), 0, 0);
  const diff = d.getTime() - start.getTime();
  const dayOfYear = Math.floor(diff / (1000 * 60 * 60 * 24));
  const index = (dayOfYear - 1) % ALL_CHALLENGES.length;
  return ALL_CHALLENGES[index];
}

export const ALL_CHALLENGES: DailyChallenge[] = [

  /* ── 1 ─────────────────────────────────────────────────────────────────── */
  {
    id: 1,
    date: "2026-04-10",
    axis: {
      label: "SOUNDS LIKE A CULT ←→ SOUNDS LIKE A YOGA CLASS",
      left_pole: "CULT",
      right_pole: "YOGA CLASS",
      description: "Is this asking you to surrender yourself — or just your Saturday morning?",
    },
    artifacts: [
      {
        id: "a",
        text: "Leave everything behind. Your old life was a preparation. The community is waiting. You are ready now.",
        category: "manifesto",
        axis_position: -2,
        highlighted_words: ["Leave everything behind", "old life", "community is waiting"],
        reveal: "Four sentences. Four imperatives. The self that arrived is described as a problem to be solved. \"Ready now\" closes the door on the question of whether you agreed to any of this.",
      },
      {
        id: "b",
        text: "This is not just a workout. This is a movement. Clip in. Find your tribe. Leave it all on the bike.",
        category: "advertising",
        axis_position: -0.9,
        highlighted_words: ["movement", "tribe", "Leave it all"],
        reveal: "The copy borrows the grammar of conversion. \"Movement\" and \"tribe\" do not belong to fitness — they belong to belonging. The bike is incidental. The subscription is not mentioned.",
      },
      {
        id: "c",
        text: "Honor your body. Release what no longer serves you. This hour belongs to you.",
        category: "wellness",
        axis_position: 1.1,
        highlighted_words: ["Honor", "Release", "no longer serves you", "belongs to you"],
        reveal: "\"No longer serves you\" treats your own feelings as employees you can terminate. The grammar is gentle. The implication — that your current self needs managing — is not.",
      },
      {
        id: "d",
        text: "Set an intention. Breathe into it. The mat is a mirror. You already have everything you need.",
        category: "wellness",
        axis_position: 1.9,
        highlighted_words: ["intention", "mirror", "already have everything"],
        reveal: "The claim that you already have everything you need is the most radical sentence here — it is the one selling the least. The mat as mirror is a metaphor so soft it almost disappears. This one means it.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
    tomorrow_axis: "YOUR BOSS WROTE THIS ←→ YOUR THERAPIST WROTE THIS",
  },

  /* ── 2 ─────────────────────────────────────────────────────────────────── */
  {
    id: 2,
    date: "2026-04-11",
    axis: {
      label: "YOUR BOSS WROTE THIS ←→ YOUR THERAPIST WROTE THIS",
      left_pole: "BOSS",
      right_pole: "THERAPIST",
      description: "Both are trying to improve your performance. They disagree on who it's for.",
    },
    artifacts: [
      {
        id: "a",
        text: "You've shown real growth potential. With focused effort in Q3, you'll be well-positioned to contribute at the next level.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["growth potential", "focused effort", "next level", "contribute"],
        reveal: "\"Contribute\" is doing significant work here. The text is enthusiastic about your future — specifically, your future usefulness. The question of whether you want to be at the next level is not raised.",
      },
      {
        id: "b",
        text: "We hold each other accountable. Feedback is a gift. We expect everyone to bring their best self to work.",
        category: "corporate",
        axis_position: -0.8,
        highlighted_words: ["hold each other accountable", "gift", "best self"],
        reveal: "\"Feedback is a gift\" is the corporate sentence most people have learned to fear. \"Best self\" implies there is a worse self present that the organization has noticed. The accountability runs in one direction.",
      },
      {
        id: "c",
        text: "You can't pour from an empty cup. Rest is not a reward — it's part of the work.",
        category: "wellness",
        axis_position: 0.9,
        highlighted_words: ["empty cup", "Rest", "part of the work"],
        reveal: "The sentence is therapeutic in tone but still frames rest as instrumental — it serves the work. You are being given permission to recover so you can produce. The cup metaphor is a container. So is the logic.",
      },
      {
        id: "d",
        text: "It sounds like you're carrying a lot right now. What would it look like to give yourself permission to say no?",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["carrying a lot", "permission", "say no"],
        reveal: "The question does not contain an answer. This is unusual. It also doesn't tell you what saying no would cost you, or what it would accomplish. It simply opens the door and waits.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
    tomorrow_axis: "WROTE THIS AT 2AM ←→ PAID A CONSULTANT $50K TO WRITE THIS",
  },

  /* ── 3 ─────────────────────────────────────────────────────────────────── */
  {
    id: 3,
    date: "2026-04-12",
    axis: {
      label: "WROTE THIS AT 2AM ←→ PAID A CONSULTANT TO WRITE THIS",
      left_pole: "2AM",
      right_pole: "CONSULTANT",
      description: "Authenticity is hard to manufacture. But it's also hard to fake sincerity after 11pm.",
    },
    artifacts: [
      {
        id: "a",
        text: "Everything is connected right now. The system isn't broken — it IS the system. I feel like I can finally see it.",
        category: "literary",
        axis_position: -2,
        highlighted_words: ["connected", "IS the system", "finally see it"],
        reveal: "The grammar of revelation at 2am: capitalization for emphasis, the word \"finally,\" the sense that perception itself has upgraded. The thought is not original. The feeling that it is — that is the hour.",
      },
      {
        id: "b",
        text: "We need to move fast. The opportunity window is closing. Here are three things we can do before Monday.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["move fast", "window is closing", "before Monday"],
        reveal: "\"Window is closing\" is urgency manufactured from nothing. \"Before Monday\" converts a philosophical problem into a calendar item. The three things have not yet been listed, but the framework for ignoring objections has been established.",
      },
      {
        id: "c",
        text: "Together, we build the future our children deserve. This is not a moment. It is a movement.",
        category: "speech",
        axis_position: 1,
        highlighted_words: ["children deserve", "not a moment", "movement"],
        reveal: "The children appear in political copy primarily as a rhetorical device. They do not vote. \"Not a moment, a movement\" has been said at enough rallies that it now reads as a template. Someone was paid to select this from among the options.",
      },
      {
        id: "d",
        text: "Our north star metric is engagement-to-conversion, optimized through continuous iteration across all touchpoints in the customer journey.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["north star metric", "optimized", "touchpoints", "customer journey"],
        reveal: "The sentence contains no subject, no verb of consequence, and no human being. It is not trying to communicate — it is demonstrating familiarity with a vocabulary. This costs between $400 and $800 per hour.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 4 ─────────────────────────────────────────────────────────────────── */
  {
    id: 4,
    date: "2026-04-13",
    axis: {
      label: "SOUNDS LIKE A STARTUP ←→ SOUNDS LIKE A GOVERNMENT",
      left_pole: "STARTUP",
      right_pole: "GOVERNMENT",
      description: "Both want to organize your life at scale. One has venture capital. The other has a navy.",
    },
    artifacts: [
      {
        id: "a",
        text: "We're disrupting how humans connect. Our product is the infrastructure for the next billion relationships.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["disrupting", "infrastructure", "billion relationships"],
        reveal: "\"Infrastructure\" and \"relationships\" do not usually occupy the same sentence. The company has decided they should. The next billion people in question were not consulted on whether they wanted their relationships disrupted.",
      },
      {
        id: "b",
        text: "Our platform enables users to access services at scale, with safety, reliability, and trust at the core.",
        category: "corporate",
        axis_position: -0.6,
        highlighted_words: ["platform", "at scale", "safety", "trust at the core"],
        reveal: "This could describe a large tech company at its most defensive, or a utility company at its most ambitious. The passive voice is doing significant diplomatic work. \"Trust at the core\" is the sentence a company writes after trust has become a problem.",
      },
      {
        id: "c",
        text: "This initiative will be phased across 18 months with inter-departmental coordination and a dedicated working group.",
        category: "speech",
        axis_position: 1,
        highlighted_words: ["phased across 18 months", "inter-departmental", "working group"],
        reveal: "The sentence describes a process, not an outcome. \"Dedicated working group\" means a meeting that will generate a report. Eighteen months is long enough to outlast most political attention spans. This is the plan.",
      },
      {
        id: "d",
        text: "Applicants must submit the relevant form in triplicate. Processing time is six to eight weeks. Incomplete submissions will not be accepted.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["triplicate", "six to eight weeks", "Incomplete submissions"],
        reveal: "This text does not want to help you. It wants to filter out people who give up easily. \"Triplicate\" is the bureaucracy's way of saying: we do not trust you, and we want you to know it.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 5 ─────────────────────────────────────────────────────────────────── */
  {
    id: 5,
    date: "2026-04-14",
    axis: {
      label: "GYM BRO MANIFESTO ←→ BUDDHIST TEXT",
      left_pole: "GYM BRO",
      right_pole: "BUDDHIST",
      description: "Both will tell you that you need to change. They disagree on what counts as progress.",
    },
    artifacts: [
      {
        id: "a",
        text: "Pain is just weakness leaving the body. No one ever got great by being comfortable. You're either growing or dying.",
        category: "manifesto",
        axis_position: -2,
        highlighted_words: ["weakness leaving", "No one ever got great", "growing or dying"],
        reveal: "The binary at the end — \"growing or dying\" — forecloses the possibility of rest as something other than failure. The body is addressed as a problem. The solution is the problem, applied harder.",
      },
      {
        id: "b",
        text: "Consistency over intensity. Show up. Put in the work. Trust the process. Results don't lie.",
        category: "advertising",
        axis_position: -0.7,
        highlighted_words: ["Consistency", "Show up", "Trust the process", "Results don't lie"],
        reveal: "\"Trust the process\" entered sports culture and never left. It asks you to defer judgment indefinitely. \"Results don't lie\" is the evidence that will eventually justify the deferral — or the sentence that ends the relationship when they don't.",
      },
      {
        id: "c",
        text: "Notice the resistance. Breathe through it. You don't need to conquer anything — only to be present.",
        category: "wellness",
        axis_position: 1,
        highlighted_words: ["resistance", "Breathe through it", "conquer", "be present"],
        reveal: "The word \"conquer\" is introduced only to be discarded. This is not neutral — it's a quiet argument against a specific worldview. \"Only to be present\" sounds easy. It is not easy. That is the point.",
      },
      {
        id: "d",
        text: "The body is a raft. It carries you across the river. You do not carry it.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["raft", "carries you", "You do not carry it"],
        reveal: "The metaphor reverses the gym bro's logic without mentioning it. The body is useful — not for conquering, but for crossing. The river is not named. You are expected to know which one.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 6 ─────────────────────────────────────────────────────────────────── */
  {
    id: 6,
    date: "2026-04-15",
    axis: {
      label: "SELLING SOMETHING ←→ GENUINELY BELIEVES THIS",
      left_pole: "SELLING",
      right_pole: "BELIEVES",
      description: "The sincerest-sounding text is not always the most sincere. Your job: find the one that means it.",
    },
    artifacts: [
      {
        id: "a",
        text: "Real people. Real stories. Real change. Because you deserve a bank that actually cares.",
        category: "advertising",
        axis_position: -2,
        highlighted_words: ["Real people", "Real change", "actually cares"],
        reveal: "\"Actually\" is the tell. It implies a standard of caring that other banks are not meeting, which the bank believes will be credible because it is true of other banks. The word \"real\" appears three times before any real thing is described.",
      },
      {
        id: "b",
        text: "I didn't get into this to be popular. I got into this because someone had to say it.",
        category: "speech",
        axis_position: -0.8,
        highlighted_words: ["not to be popular", "someone had to say it"],
        reveal: "\"Someone had to say it\" is a claim that is almost always made about things that have already been said many times. The framing positions the speaker as a lonely truth-teller. This is a charismatic posture. It may also be accurate.",
      },
      {
        id: "c",
        text: "We're not a PAC. We're just neighbors who are tired and decided to do something about it.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["just neighbors", "tired", "do something about it"],
        reveal: "\"Just neighbors\" is doing structural work — it positions the group outside the system of organized politics even if the group is organized. \"Tired\" is the most honest word here. Exhaustion is not a posture that is easy to perform convincingly.",
      },
      {
        id: "d",
        text: "I could have stayed quiet. It was easier. But I looked at my daughter and thought: not this time.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["stayed quiet", "easier", "not this time"],
        reveal: "The child appears not as rhetoric but as witness. The sentence doesn't promise anything — it describes a decision already made. \"Not this time\" implies previous times of staying quiet. This one has been drafted in the body for a while.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 7 ─────────────────────────────────────────────────────────────────── */
  {
    id: 7,
    date: "2026-04-16",
    axis: {
      label: "SOUNDS LIKE A THREAT ←→ SOUNDS LIKE CUSTOMER SERVICE",
      left_pole: "THREAT",
      right_pole: "CUSTOMER SERVICE",
      description: "Both are managing your expectations. One has already decided how this ends.",
    },
    artifacts: [
      {
        id: "a",
        text: "Continued use of this service constitutes acceptance of all terms, including mandatory arbitration and class action waiver.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["Continued use", "mandatory arbitration", "class action waiver"],
        reveal: "The legal innovation here is that continuing to do what you were already doing now counts as signing a contract. You have been opted in by existing. The arbitration clause means that disputes about this will be settled by someone the company has a relationship with.",
      },
      {
        id: "b",
        text: "We take your feedback very seriously. A senior member of our team will be in touch within 72 hours.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["very seriously", "senior member", "72 hours"],
        reveal: "\"Very seriously\" is the corporate phrase for: we have received your complaint and routed it to the correct folder. The specificity of \"72 hours\" is designed to feel like urgency. It is the opposite of urgency.",
      },
      {
        id: "c",
        text: "We're so sorry for the inconvenience. As a gesture of goodwill, please accept a 10% discount on your next purchase.",
        category: "corporate",
        axis_position: 0.8,
        highlighted_words: ["gesture of goodwill", "10%", "next purchase"],
        reveal: "The discount presupposes a next purchase, which the company has decided will occur regardless of this experience. \"Gesture of goodwill\" is the phrase for a compensation calculated to cost less than the complaint. It works most of the time.",
      },
      {
        id: "d",
        text: "I've personally looked into your case and I understand why you're frustrated. Here's what I'm doing right now.",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["personally", "understand why", "right now"],
        reveal: "\"Personally\" and \"right now\" are not available to systems, only to people. This sentence has a subject. The subject is taking action in the present tense. This is unusual enough to note.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 8 ─────────────────────────────────────────────────────────────────── */
  {
    id: 8,
    date: "2026-04-17",
    axis: {
      label: "SOUNDS LIKE 1984 ←→ SOUNDS LIKE A LINKEDIN POST",
      left_pole: "1984",
      right_pole: "LINKEDIN",
      description: "One was a warning. The other is Tuesday.",
    },
    artifacts: [
      {
        id: "a",
        text: "Non-compliant behaviors will be documented. Colleagues are encouraged to report concerns to the appropriate channel.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["Non-compliant", "documented", "report concerns"],
        reveal: "\"Appropriate channel\" is the modern equivalent of \"the committee.\" The encouragement to report colleagues is framed as civic virtue. The passive construction — \"will be documented\" — removes the documenter from view.",
      },
      {
        id: "b",
        text: "Our employee experience platform ensures productivity and protects company assets. Transparency builds trust.",
        category: "corporate",
        axis_position: -0.9,
        highlighted_words: ["employee experience platform", "protects company assets", "Transparency builds trust"],
        reveal: "\"Employee experience platform\" is a monitoring tool whose name has been selected to suggest the opposite of monitoring. The final sentence — \"transparency builds trust\" — applies to the employees, not to the company.",
      },
      {
        id: "c",
        text: "I wake up at 4:30am. Not because I have to. Because the person I want to be is already awake.",
        category: "linkedin",
        axis_position: 0.9,
        highlighted_words: ["4:30am", "person I want to be", "already awake"],
        reveal: "The future self has been externalized into a competitor who has a better sleep schedule. The present self is losing. The solution is to wake up earlier, which will not close the gap because the future self will also get up earlier.",
      },
      {
        id: "d",
        text: "Grateful. Humbled. Blessed. This journey has taught me that failure is just data. Here's what my worst quarter taught me about leadership.",
        category: "linkedin",
        axis_position: 2,
        highlighted_words: ["Grateful. Humbled. Blessed.", "failure is just data", "worst quarter"],
        reveal: "The opening triad — three words, three periods — is a liturgical structure borrowed from somewhere older. \"Failure is just data\" converts a human experience into an asset. The worst quarter will now generate content for six months.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 9 ─────────────────────────────────────────────────────────────────── */
  {
    id: 9,
    date: "2026-04-18",
    axis: {
      label: "YOUR MOM WOULD SHARE THIS ←→ YOUR KID WOULD SHARE THIS",
      left_pole: "MOM SHARE",
      right_pole: "KID SHARE",
      description: "Two different algorithms. One for nostalgia. One for irony. Both are exactly right.",
    },
    artifacts: [
      {
        id: "a",
        text: "Dance like nobody's watching. Laugh like nobody's listening. Love like you've never been hurt.",
        category: "literary",
        axis_position: -2,
        highlighted_words: ["Dance like nobody's watching", "never been hurt"],
        reveal: "The advice requires you to forget your audience, your ears, and your entire relationship history simultaneously. It is technically impossible. The impossibility is the point — this text is offering a feeling, not an instruction.",
      },
      {
        id: "b",
        text: "They said it couldn't be done. They were wrong. If you can dream it, you can achieve it.",
        category: "advertising",
        axis_position: -0.8,
        highlighted_words: ["They said it couldn't", "dream it", "achieve it"],
        reveal: "\"They\" — the skeptics — appear in this text only to be defeated. The victory belongs to you before you've done anything. \"Dream it, achieve it\" rhymes, which is doing the work that evidence would otherwise need to do.",
      },
      {
        id: "c",
        text: "I asked my company for a raise. They said we're a family. I said families pay child support.",
        category: "lyric",
        axis_position: 0.9,
        highlighted_words: ["we're a family", "child support"],
        reveal: "The joke lands because \"we're a family\" is a real phrase used by real companies, and the rebuttal is already implied by it. The humor works as diagnosis. The person asking for a raise did not get one.",
      },
      {
        id: "d",
        text: "The audacity of waking up every day and continuing to participate in society. Respect yourself honestly.",
        category: "lyric",
        axis_position: 2,
        highlighted_words: ["audacity", "continuing to participate", "Respect yourself"],
        reveal: "The sentence treats the continuation of daily life as a form of heroism — which is ironic, except that it also isn't. \"Honestly\" at the end transforms the compliment into a challenge. This genre requires you to hold both readings at once.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 10 ────────────────────────────────────────────────────────────────── */
  {
    id: 10,
    date: "2026-04-19",
    axis: {
      label: "SOUNDS LIKE SCIENCE ←→ SOUNDS LIKE ASTROLOGY",
      left_pole: "SCIENCE",
      right_pole: "ASTROLOGY",
      description: "Both use specialized vocabulary to explain why things happen to you specifically.",
    },
    artifacts: [
      {
        id: "a",
        text: "The null hypothesis was rejected at p < 0.05. Effect size was modest. Replication is pending.",
        category: "literary",
        axis_position: -2,
        highlighted_words: ["null hypothesis", "p < 0.05", "modest", "Replication is pending"],
        reveal: "The phrase \"replication is pending\" is the most important sentence here, and the most honest. It means: we found something, and we are not sure yet whether we found it or invented it. Science in its most functional form sounds like uncertainty.",
      },
      {
        id: "b",
        text: "Research suggests that gut microbiome diversity correlates with mood regulation and cognitive function.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["Research suggests", "correlates with", "gut microbiome"],
        reveal: "\"Research suggests\" is not \"research shows.\" \"Correlates with\" is not \"causes.\" The sentence is technically accurate and structured to sound more definitive than it is. This is how preliminary findings become the basis for a supplement line.",
      },
      {
        id: "c",
        text: "Your attachment style — likely formed in early childhood — determines your relationship patterns today.",
        category: "wellness",
        axis_position: 0.9,
        highlighted_words: ["attachment style", "early childhood", "determines"],
        reveal: "\"Determines\" is doing more work than the research supports. Attachment theory has empirical roots, but the pop-psychology version flattens probability into destiny. The past becomes a fixed variable. The therapist's office is open Tuesday and Thursday.",
      },
      {
        id: "d",
        text: "Mars in retrograde amplifies communication breakdowns. This is a time for reflection, not action.",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["Mars in retrograde", "amplifies", "reflection, not action"],
        reveal: "Mars is a planet. It does not know you are trying to send an email. What retrograde actually describes is an optical illusion from Earth's perspective. The prescription — \"reflection, not action\" — is useful advice issued on a false premise, which is the tradition of many useful things.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 11 ────────────────────────────────────────────────────────────────── */
  {
    id: 11,
    date: "2026-04-20",
    axis: {
      label: "SOUNDS SINCERE ←→ SOUNDS COACHED",
      left_pole: "SINCERE",
      right_pole: "COACHED",
      description: "You can't always tell. That's why this is the game.",
    },
    artifacts: [
      {
        id: "a",
        text: "I've been thinking about what you said for three weeks. You were right. I didn't want to admit it.",
        category: "literary",
        axis_position: -2,
        highlighted_words: ["three weeks", "You were right", "didn't want to admit"],
        reveal: "The specificity of \"three weeks\" is hard to perform. Admitting you didn't want to admit something is a second admission that sits inside the first one. This sentence could not have been workshopped into existence.",
      },
      {
        id: "b",
        text: "Look, I don't have a great answer for that. I got that one wrong, and I own it.",
        category: "speech",
        axis_position: -0.8,
        highlighted_words: ["I don't have a great answer", "I got that one wrong", "I own it"],
        reveal: "\"I own it\" is a coached phrase. But the sentence before it — \"I don't have a great answer\" — is an unusual thing for a prepared speaker to say. The combination is either authentic or a very good simulation of it. The distinction may not matter.",
      },
      {
        id: "c",
        text: "I take full responsibility. We fell short of our values, and I am committed — fully committed — to doing the work.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["full responsibility", "fell short of our values", "fully committed", "doing the work"],
        reveal: "\"Full responsibility\" followed by no consequences is the structure of the modern non-apology. \"Fell short of our values\" frames a failure as a gap rather than a choice. \"The work\" is named but not described. A communications team was involved.",
      },
      {
        id: "d",
        text: "I want to be very clear: we heard you. And we are committed — fully committed — to doing better going forward.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["very clear", "we heard you", "fully committed", "going forward"],
        reveal: "The phrase \"going forward\" is the tell. It is the corporate equivalent of \"from now on,\" which carries the implicit acknowledgment that before this moment, things were different. \"We heard you\" arrives two press cycles after the problem. The sentence was drafted in parallel with the investigation.",
      },
    ],
    correct_order: ["d", "c", "b", "a"],
  },

  /* ── 12 ────────────────────────────────────────────────────────────────── */
  {
    id: 12,
    date: "2026-04-21",
    axis: {
      label: "MLM PITCH ←→ PERSONAL GROWTH BOOK",
      left_pole: "MLM",
      right_pole: "GROWTH BOOK",
      description: "Both want you to believe your current life is a chrysalis. One will send you a starter kit.",
    },
    artifacts: [
      {
        id: "a",
        text: "I'm not selling a product. I'm offering you financial freedom. You just have to be willing to invest in yourself.",
        category: "advertising",
        axis_position: -2,
        highlighted_words: ["financial freedom", "invest in yourself"],
        reveal: "\"I'm not selling a product\" is the first sentence of a product pitch. \"Invest in yourself\" is the euphemism for the upfront cost. The pitch has rotated the mirror so you are looking at yourself, not at the transaction.",
      },
      {
        id: "b",
        text: "When I started this journey, I was working 60 hours a week and still broke. Now I set my own schedule.",
        category: "linkedin",
        axis_position: -0.8,
        highlighted_words: ["this journey", "60 hours a week", "set my own schedule"],
        reveal: "The before-and-after narrative is the oldest sales structure in existence. The before is specific (60 hours, broke); the after is vague (sets own schedule). The mechanism connecting them is the product being sold, which is mentioned after the testimony.",
      },
      {
        id: "c",
        text: "You are not behind. You are not failing. You are becoming.",
        category: "wellness",
        axis_position: 0.9,
        highlighted_words: ["not behind", "not failing", "becoming"],
        reveal: "The three negations arrive before the positive. \"Becoming\" is the payoff — but becoming what, at what pace, is left open. This is compassionate. It is also possible to read as: your timeline is indefinitely deferred and that's okay.",
      },
      {
        id: "d",
        text: "Most advice about change is wrong. Change is slow, uncomfortable, and happens mostly while you sleep.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["most advice about change is wrong", "slow", "while you sleep"],
        reveal: "The opening sentence is designed to neutralize competing claims, including the one you might have read last month. \"While you sleep\" is the anti-hustle punchline — and also, incidentally, true. This book will not sell as many copies.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 13 ────────────────────────────────────────────────────────────────── */
  {
    id: 13,
    date: "2026-04-22",
    axis: {
      label: "STARTUP PITCH ←→ RELIGIOUS TEXT",
      left_pole: "STARTUP",
      right_pole: "RELIGIOUS TEXT",
      description: "Both are offering salvation. The valuations differ.",
    },
    artifacts: [
      {
        id: "a",
        text: "We're not building an app. We're building the infrastructure for human flourishing at scale.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["not building an app", "infrastructure", "human flourishing at scale"],
        reveal: "\"Human flourishing\" has been borrowed from philosophy and placed in a pitch deck. \"At scale\" converts the aspiration into a growth metric. The app — which is what they are building — is mentioned only to be disclaimed.",
      },
      {
        id: "b",
        text: "Imagine a world where every child has access to the tools they need to reach their full potential.",
        category: "speech",
        axis_position: -0.7,
        highlighted_words: ["Imagine", "every child", "full potential"],
        reveal: "\"Imagine\" opens the sentence, which signals: this world does not exist yet, and we are the ones who will build it. \"Full potential\" is the endpoint — a phrase so large it cannot be measured, which makes it impossible to fail to achieve.",
      },
      {
        id: "c",
        text: "The kingdom is not coming. It is already here, among you, if you know how to look.",
        category: "literary",
        axis_position: 0.8,
        highlighted_words: ["not coming", "already here", "if you know how to look"],
        reveal: "The present tense is the theological move. The kingdom does not require infrastructure or a Series B — only a change in perception. \"If you know how to look\" places the obstacle inside the seeker, not inside history.",
      },
      {
        id: "d",
        text: "What does it profit a person to gain the whole world and lose themselves in the process?",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["profit", "gain the whole world", "lose themselves"],
        reveal: "The question uses the language of commerce — \"profit\" — to critique a commercial logic. This was not an accident. The text has been asking this question for two thousand years, which gives it a replication rate most studies cannot match.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 14 ────────────────────────────────────────────────────────────────── */
  {
    id: 14,
    date: "2026-04-23",
    axis: {
      label: "SOUNDS LIKE YOUR HOROSCOPE ←→ SOUNDS LIKE ECONOMIC POLICY",
      left_pole: "HOROSCOPE",
      right_pole: "POLICY",
      description: "Both will tell you forces beyond your control are shaping your future. One uses the word inflation.",
    },
    artifacts: [
      {
        id: "a",
        text: "A period of uncertainty gives way to clarity. The resources you need are closer than you think.",
        category: "wellness",
        axis_position: -2,
        highlighted_words: ["period of uncertainty", "clarity", "closer than you think"],
        reveal: "The horoscope performs a service: it names the anxiety without specifying its cause, then resolves it without specifying a mechanism. \"Closer than you think\" is unfalsifiable. It is also, statistically, often true.",
      },
      {
        id: "b",
        text: "The market rewards patience. Your financial future depends on decisions you make in the next 90 days.",
        category: "advertising",
        axis_position: -0.7,
        highlighted_words: ["market rewards patience", "90 days"],
        reveal: "The first sentence is long-term. The second is a Q1 deadline. They contradict each other, which is not unusual in financial copy. \"The next 90 days\" is a horoscope written in the language of quarterly earnings.",
      },
      {
        id: "c",
        text: "Consumer confidence remains fragile amid elevated borrowing costs and persistent core inflation.",
        category: "corporate",
        axis_position: 0.9,
        highlighted_words: ["Consumer confidence", "fragile", "elevated borrowing costs", "persistent core inflation"],
        reveal: "\"Fragile\" is a word with emotional range placed in a sentence that forbids emotion. \"Consumer confidence\" is a measurement of feelings that has been converted into an economic indicator. This sentence describes your anxiety using the vocabulary of someone who does not experience it.",
      },
      {
        id: "d",
        text: "The Committee will continue to assess incoming data and adjust the policy rate as appropriate to return inflation to target.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["Committee", "assess incoming data", "as appropriate", "return inflation to target"],
        reveal: "The subject of this sentence — \"the Committee\" — meets eight times a year and its decisions affect the mortgage payments of everyone reading this. \"As appropriate\" is the phrase that means: we will do what we decide to do, and we will tell you afterward.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 15 ────────────────────────────────────────────────────────────────── */
  {
    id: 15,
    date: "2026-04-24",
    axis: {
      label: "WELLNESS BRAND ←→ PHARMACEUTICAL AD",
      left_pole: "WELLNESS BRAND",
      right_pole: "PHARMA AD",
      description: "Both are selling relief. One has FDA approval. Neither will name what's wrong with you.",
    },
    artifacts: [
      {
        id: "a",
        text: "Reset your nervous system. Rebalance your gut. Reclaim your energy. You deserve to feel like yourself again.",
        category: "advertising",
        axis_position: -2,
        highlighted_words: ["Reset", "Rebalance", "Reclaim", "feel like yourself"],
        reveal: "The three imperatives are medical-adjacent without being medical claims. \"Deserve\" converts a health outcome into a moral entitlement. \"Feel like yourself again\" implies the problem is that you have stopped being yourself — which is a more expansive diagnosis than any doctor would make.",
      },
      {
        id: "b",
        text: "Clinically studied ingredients to support your body's natural processes. Feel the difference in 30 days.",
        category: "advertising",
        axis_position: -0.7,
        highlighted_words: ["Clinically studied", "natural processes", "30 days"],
        reveal: "\"Clinically studied\" is not \"clinically proven\" — the study exists, but the outcome is not guaranteed by the phrase. \"Natural processes\" signals that the product is helping you be more you, which is different from treating a condition. The 30-day window is the refund policy.",
      },
      {
        id: "c",
        text: "Living with this condition is hard. But there are options. Ask your doctor if this treatment is right for you.",
        category: "advertising",
        axis_position: 0.9,
        highlighted_words: ["condition", "options", "Ask your doctor"],
        reveal: "The condition is named in the full ad, but this excerpt reads as a category. \"Ask your doctor\" is the regulatory-compliant handoff — the company has told you about the drug without prescribing it. Your doctor, who has seven minutes, will now complete the sale.",
      },
      {
        id: "d",
        text: "Side effects may include nausea, dizziness, and in rare cases, thoughts of self-harm. Do not stop taking this medication without consulting your doctor.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["Side effects", "rare cases", "Do not stop"],
        reveal: "The pharmaceutical ad is the only text in any medium that is legally required to tell you the ways it might hurt you. This is the most honest sentence in the category, and it is read by a fast voice at the end of a television spot about people playing frisbee.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 16 ────────────────────────────────────────────────────────────────── */
  {
    id: 16,
    date: "2026-04-25",
    axis: {
      label: "SOUNDS LIKE A COMPLIMENT ←→ SOUNDS LIKE A THREAT",
      left_pole: "COMPLIMENT",
      right_pole: "THREAT",
      description: "The difference is sometimes just the relationship. And the power dynamic.",
    },
    artifacts: [
      {
        id: "a",
        text: "You handled that beautifully. I learned something watching you work.",
        category: "speech",
        axis_position: -2,
        highlighted_words: ["beautifully", "learned something", "watching you work"],
        reveal: "The admiration is specific — \"watching you work\" means the observation was real, not performed. \"I learned something\" places the speaker below the person being praised, which requires either confidence or truth. This one costs nothing to say. It is the rarest kind.",
      },
      {
        id: "b",
        text: "You're so brave for sharing that idea. It takes real courage to put something that unconventional out there.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["brave", "real courage", "unconventional"],
        reveal: "\"Brave\" and \"courage\" are words reserved for things that are risky. Calling an idea unconventional is the compliment that contains its own verdict. The speaker has praised and dismissed in the same breath without technically doing either.",
      },
      {
        id: "c",
        text: "You've exceeded every expectation I had for you. I'd hate to see you plateau here.",
        category: "corporate",
        axis_position: 0.9,
        highlighted_words: ["exceeded every expectation", "I'd hate to see you plateau"],
        reveal: "The sentence pivots on the word \"but\" that isn't written. The second clause converts the compliment into a warning. \"I'd hate to see\" positions the speaker as caring — while the content of the sentence is a threat dressed in disappointment.",
      },
      {
        id: "d",
        text: "I want you to know I'm watching your progress very closely. I see everything.",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["watching your progress", "very closely", "I see everything"],
        reveal: "This sentence requires no interpretation. Surveillance described as attention is still surveillance. \"I see everything\" is either a performance review or a horror film. The context determines which. In some workplaces, these are the same.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 17 ────────────────────────────────────────────────────────────────── */
  {
    id: 17,
    date: "2026-04-26",
    axis: {
      label: "SOUNDS REVOLUTIONARY ←→ SOUNDS LIKE A BRAND",
      left_pole: "REVOLUTIONARY",
      right_pole: "BRAND",
      description: "At some point the revolution got a Pantone color and a font. Your job: find where.",
    },
    artifacts: [
      {
        id: "a",
        text: "The owners of this system have never needed your permission and they will never voluntarily return it.",
        category: "manifesto",
        axis_position: -2,
        highlighted_words: ["owners of this system", "never needed your permission", "never voluntarily return"],
        reveal: "The sentence describes a power relationship accurately. It is not asking you to feel good about this — it is asking you to be clear about it. There is no product at the end. There is also no plan. This is the text that generates the next three.",
      },
      {
        id: "b",
        text: "The power structure will not reform itself. We are not asking. We are building alternatives.",
        category: "manifesto",
        axis_position: -0.8,
        highlighted_words: ["power structure", "not asking", "building alternatives"],
        reveal: "The movement from critique to construction is the maturation of the previous sentence. \"We are building alternatives\" is both more actionable and more likely to be absorbed by the system it is critiquing. This is the paragraph that appears in the company's origin story three years later.",
      },
      {
        id: "c",
        text: "We stand with our community. The climate is not a side. Justice is not a talking point. Love is not a policy position.",
        category: "corporate",
        axis_position: 0.9,
        highlighted_words: ["We stand with", "not a side", "not a talking point", "not a policy position"],
        reveal: "The structure — \"X is not just Y\" — is borrowed from activist language and used here to sell products to people who use activist language. The company's supply chain is not mentioned. The statement will be updated if the political environment changes.",
      },
      {
        id: "d",
        text: "We're changing the system from within. One conscious purchase at a time.",
        category: "advertising",
        axis_position: 2,
        highlighted_words: ["changing the system", "conscious purchase"],
        reveal: "\"Changing the system from within\" is the argument for incrementalism. \"One conscious purchase at a time\" converts political action into a transaction. The revolution is available in your size. Free shipping on orders over $75.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 18 ────────────────────────────────────────────────────────────────── */
  {
    id: 18,
    date: "2026-04-27",
    axis: {
      label: "SOUNDS LIKE FREEDOM ←→ SOUNDS LIKE LONELINESS",
      left_pole: "FREEDOM",
      right_pole: "LONELINESS",
      description: "The same life, described two ways. You decide which one is true.",
    },
    artifacts: [
      {
        id: "a",
        text: "I answer to no one. My time is completely my own. I've designed a life with no obligations.",
        category: "linkedin",
        axis_position: -2,
        highlighted_words: ["answer to no one", "completely my own", "no obligations"],
        reveal: "\"No obligations\" sounds like freedom until you notice that obligations are also what people call relationships. The person answering to no one has no one asking. This is one reading. The speaker would prefer the other.",
      },
      {
        id: "b",
        text: "I work from wherever I want, whenever I want. Last week: Bali. This week: who knows.",
        category: "linkedin",
        axis_position: -0.7,
        highlighted_words: ["wherever I want", "whenever I want", "who knows"],
        reveal: "The geographic freedom is real. \"Who knows\" is positioned as romance but it is also an accurate description of uncertainty about the future. The apartment is not mentioned. Nor is the time zone of anyone who might want to call.",
      },
      {
        id: "c",
        text: "Most evenings I eat alone. I used to think I liked it. Now I'm less sure.",
        category: "literary",
        axis_position: 0.9,
        highlighted_words: ["eat alone", "used to think I liked it", "less sure"],
        reveal: "The shift from past tense to present uncertainty is the confession the other artifacts in this set have been avoiding. \"Less sure\" is not a crisis — it is honest. The plate is still there. The table is still set.",
      },
      {
        id: "d",
        text: "I keep telling people I'm living the dream. I'm not sure they believe me anymore. I'm not sure I do.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["living the dream", "not sure they believe me", "not sure I do"],
        reveal: "The sentence tracks the erosion of a story in real time. The dream was sold first to others, then to oneself. The doubt arrives in layers: their disbelief first, then the admission that theirs mirrors yours. This is the axis, resolved.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 19 ────────────────────────────────────────────────────────────────── */
  {
    id: 19,
    date: "2026-04-28",
    axis: {
      label: "HUSTLE CULTURE ←→ ACTUAL WISDOM",
      left_pole: "HUSTLE",
      right_pole: "WISDOM",
      description: "One of these has been optimized. The other has been tested.",
    },
    artifacts: [
      {
        id: "a",
        text: "Sleep is for people who've already won. Until then: ship, iterate, repeat. The work is the answer.",
        category: "linkedin",
        axis_position: -2,
        highlighted_words: ["Sleep is for people who've already won", "ship, iterate, repeat"],
        reveal: "The sentence uses \"won\" as the terminal state, which implies there is a score. Sleep deprivation is the sacrifice that proves commitment. The research on sleep deprivation and decision-making is not cited. This is consistent with the advice.",
      },
      {
        id: "b",
        text: "Your potential is unlimited. The only thing between you and success is the story you tell yourself.",
        category: "advertising",
        axis_position: -0.8,
        highlighted_words: ["unlimited", "story you tell yourself"],
        reveal: "\"The only thing\" is doing heavy lifting in this sentence. It excludes structural factors, material conditions, and the possibility that potential is, in fact, distributed unevenly. The empowerment is offered without cost because the obstacle has been placed entirely inside you.",
      },
      {
        id: "c",
        text: "A good plan today is better than a perfect plan tomorrow.",
        category: "literary",
        axis_position: 0.9,
        highlighted_words: ["good plan today", "perfect plan tomorrow"],
        reveal: "The sentence earns its compression. It has been refined enough to say something true in eleven words. It does not explain itself. This is the structure of a sentence that has survived long enough to lose its context and keep its meaning.",
      },
      {
        id: "d",
        text: "You will work very hard for things that will not matter. This is not a failure. This is how you find out what does.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["will not matter", "not a failure", "find out what does"],
        reveal: "The sentence contradicts the premise of most career advice by naming the waste as the method. \"This is not a failure\" is the most important clause — it removes the shame from the process of elimination. This could not be monetized into a course.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 20 ────────────────────────────────────────────────────────────────── */
  {
    id: 20,
    date: "2026-04-29",
    axis: {
      label: "SOUNDS INEVITABLE ←→ SOUNDS LIKE A CHOICE",
      left_pole: "INEVITABLE",
      right_pole: "CHOICE",
      description: "History is written by people who needed it to sound like it couldn't have gone any other way.",
    },
    artifacts: [
      {
        id: "a",
        text: "The market always finds equilibrium. Disruption is the engine of progress. This is simply how innovation works.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["always finds equilibrium", "engine of progress", "simply how"],
        reveal: "\"Simply\" is the word you use when you want the listener to feel naive for asking further questions. \"Always finds equilibrium\" describes a tendency as a law. The workers displaced by disruption are in the equilibrium — they are just not in this sentence.",
      },
      {
        id: "b",
        text: "AI will transform every industry. The question is not whether, but when — and whether you'll be ready.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["transform every industry", "not whether, but when", "whether you'll be ready"],
        reveal: "The transformation is declared fait accompli before it is complete. \"Not whether, but when\" converts a prediction into a schedule. The final question — \"whether you'll be ready\" — transfers the uncertainty from the technology to you.",
      },
      {
        id: "c",
        text: "We can choose a different path. These are policy decisions, not laws of nature.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["choose", "policy decisions", "not laws of nature"],
        reveal: "The sentence is doing something rare: it is insisting on contingency against an opponent who benefits from the appearance of necessity. \"Laws of nature\" is the metaphor the other side prefers. Naming it as a metaphor is the first move in changing it.",
      },
      {
        id: "d",
        text: "None of this was preordained. Every system that exists was chosen, argued over, and imposed. It can be unchosen.",
        category: "manifesto",
        axis_position: 2,
        highlighted_words: ["None of this was preordained", "chosen, argued over, and imposed", "unchosen"],
        reveal: "\"Unchosen\" is not a standard word, which is part of its force. The sentence's argument is historical: every present arrangement was once a proposal. This is the most hopeful sentence in today's set. It is also the most demanding.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 21 ────────────────────────────────────────────────────────────────── */
  {
    id: 21,
    date: "2026-04-30",
    axis: {
      label: "SOUNDS LIKE A RESIGNATION LETTER ←→ SOUNDS LIKE A LINKEDIN ANNOUNCEMENT",
      left_pole: "RESIGNATION",
      right_pole: "ANNOUNCEMENT",
      description: "One is leaving. One is branding the departure. They sometimes arrive on the same day.",
    },
    artifacts: [
      {
        id: "a",
        text: "After much reflection, I have decided to pursue other opportunities. I am grateful for the time spent here.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["much reflection", "other opportunities", "grateful"],
        reveal: "\"Other opportunities\" is the phrase that does not name what those opportunities are or why the current one is being abandoned. \"Much reflection\" suggests a decision made weeks ago. \"Grateful\" is the word you use when you are not allowed to use the word you actually mean.",
      },
      {
        id: "b",
        text: "It is with mixed emotions that I share that today is my last day. This chapter has shaped who I am as a professional.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["mixed emotions", "last day", "chapter has shaped"],
        reveal: "\"Mixed emotions\" is accurate and therefore unusual for this genre. \"Chapter\" converts a job into a narrative, which is the first step toward reframing departure as authorship. \"Professional\" is doing the work that \"person\" declined to do.",
      },
      {
        id: "c",
        text: "I'm stepping into my next chapter. I'll be sharing more very soon. Stay tuned — the best is ahead.",
        category: "linkedin",
        axis_position: 0.9,
        highlighted_words: ["next chapter", "sharing more very soon", "Stay tuned"],
        reveal: "\"Stay tuned\" is the grammar of broadcasting. The person is now a channel. \"The best is ahead\" is a claim about the future made as if it were a forecast. The announcement contains no information, which is intentional — the information will be monetized separately.",
      },
      {
        id: "d",
        text: "I left a six-figure salary and a corner office to follow my purpose. Best decision I ever made. Here's what happened next.",
        category: "linkedin",
        axis_position: 2,
        highlighted_words: ["six-figure salary", "corner office", "follow my purpose", "what happened next"],
        reveal: "The salary is named so the sacrifice can be measured. \"Follow my purpose\" is the phrase that replaces the name of what they actually did next. \"Here's what happened next\" is the click. The post ends here. The full story is a paid newsletter.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 22 ────────────────────────────────────────────────────────────────── */
  {
    id: 22,
    date: "2026-05-01",
    axis: {
      label: "LOVE LANGUAGE ←→ DEPENDENCY LANGUAGE",
      left_pole: "DEPENDENCY",
      right_pole: "LOVE",
      description: "Attachment research says there's a difference. The difference is sometimes very small.",
    },
    artifacts: [
      {
        id: "a",
        text: "You complete me. I don't know who I am without you. I need you like I need air.",
        category: "lyric",
        axis_position: -2,
        highlighted_words: ["complete me", "don't know who I am without you", "need you like I need air"],
        reveal: "Three ways of saying the same thing: you are a prerequisite for my existence. This is the vocabulary of romantic intensity, which is sometimes love and sometimes the onset of a particular kind of trouble. The air metaphor is the most honest: necessities, when removed, cause distress.",
      },
      {
        id: "b",
        text: "I just want us to be everything to each other. Is that too much to ask?",
        category: "literary",
        axis_position: -0.8,
        highlighted_words: ["everything to each other", "too much to ask"],
        reveal: "The question — \"is that too much to ask?\" — already knows the answer and is daring the other person to give it. \"Everything\" is the scope of the request, which leaves room for nothing else. The grammar of this sentence is a closed circle.",
      },
      {
        id: "c",
        text: "I choose you every day. Not because I can't live without you — but because I don't want to.",
        category: "literary",
        axis_position: 0.9,
        highlighted_words: ["choose you every day", "can't live without", "don't want to"],
        reveal: "The distinction — can't vs. won't — is the whole argument. The first is need, the second is preference. Preference requires a continuous decision, which means the relationship is reconsidered daily and confirmed. This is more demanding than dependency, and more generous.",
      },
      {
        id: "d",
        text: "You have your life. I have mine. And then there's this, which is something different and good.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["your life", "mine", "something different and good"],
        reveal: "The separateness is named before the togetherness. \"Something different\" is the honest word for love — it doesn't try to name it. \"And good\" is the quietest possible endorsement, offered without fanfare. This sentence has been arrived at.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 23 ────────────────────────────────────────────────────────────────── */
  {
    id: 23,
    date: "2026-05-02",
    axis: {
      label: "SOUNDS LIKE OPTIMISM ←→ SOUNDS LIKE DENIAL",
      left_pole: "DENIAL",
      right_pole: "OPTIMISM",
      description: "The tone is identical. The facts are different. You won't always know which this is until later.",
    },
    artifacts: [
      {
        id: "a",
        text: "Everything is fine. This is just a temporary setback. We've been through worse. Trust the process.",
        category: "speech",
        axis_position: -2,
        highlighted_words: ["Everything is fine", "temporary setback", "been through worse", "Trust the process"],
        reveal: "Four reassurances in four sentences is one too many. Each one cancels the last because a truly fine situation doesn't require this much reassurance. \"Trust the process\" asks you to defer judgment, which is useful if there is a process and it is trustworthy.",
      },
      {
        id: "b",
        text: "Every challenge is a growth opportunity. There are no bad outcomes — only lessons.",
        category: "wellness",
        axis_position: -0.7,
        highlighted_words: ["growth opportunity", "no bad outcomes", "only lessons"],
        reveal: "\"No bad outcomes\" is a claim that is testable and false. Some outcomes are bad. The sentence's purpose is to prevent the experience of badness from becoming a conclusion, which is sometimes useful and sometimes a way to avoid accountability.",
      },
      {
        id: "c",
        text: "It's bad right now. I know that. And I also know that things that seem permanent rarely are.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["bad right now", "I know that", "seem permanent rarely are"],
        reveal: "The acknowledgment arrives first, before the reassurance. \"I know that\" earns the optimism that follows. \"Seem permanent rarely are\" is a historical claim, not a promise — which is the difference between optimism and salesmanship.",
      },
      {
        id: "d",
        text: "I don't think it'll be okay because things work out. I think it'll be okay because I've seen what people do when they have to.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["not because things work out", "seen what people do", "when they have to"],
        reveal: "The source of the optimism is evidence, not faith. \"When they have to\" is the key phrase — it acknowledges that the situation will require something. The confidence is in the response, not in the outcome. This is optimism with its eyes open.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 24 ────────────────────────────────────────────────────────────────── */
  {
    id: 24,
    date: "2026-05-03",
    axis: {
      label: "SOUNDS LIKE THE GOVERNMENT ←→ SOUNDS LIKE A PARENT",
      left_pole: "GOVERNMENT",
      right_pole: "PARENT",
      description: "Both are managing you for your own good. Only one of them you chose.",
    },
    artifacts: [
      {
        id: "a",
        text: "Residents must comply with all applicable ordinances. Non-compliance may result in enforcement action.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["must comply", "applicable ordinances", "enforcement action"],
        reveal: "The passive construction — \"may result in\" — is the state's way of saying: a person will decide what happens to you, but that person will not be named in this document. \"Enforcement action\" is the clinical term for consequences applied by someone with a badge.",
      },
      {
        id: "b",
        text: "This initiative aims to ensure equitable access to essential services across all affected demographics.",
        category: "speech",
        axis_position: -0.7,
        highlighted_words: ["equitable access", "essential services", "affected demographics"],
        reveal: "The people this policy is about appear as \"affected demographics,\" which is how you refer to a population when you need to discuss them without involving them. \"Aims to ensure\" is the legislative version of \"we're really trying.\"",
      },
      {
        id: "c",
        text: "In this house, we talk about our feelings. We find solutions that work for everyone. Punishment is off the table.",
        category: "speech",
        axis_position: 0.8,
        highlighted_words: ["in this house", "feelings", "everyone", "Punishment is off the table"],
        reveal: "\"In this house\" is the jurisdiction declaration. \"Punishment is off the table\" is a policy announcement made to the people who will test it. The house has a constitution. It was not ratified — it was announced.",
      },
      {
        id: "d",
        text: "Because I said so. Because I love you. Because I'm not going to watch you make the mistake I made.",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["Because I said so", "Because I love you", "mistake I made"],
        reveal: "The three \"because\" clauses move from authority to love to personal history. Only the last one explains anything. The disclosure — \"the mistake I made\" — is what separates this from the bureaucratic texts above it. The government does not make this admission.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 25 ────────────────────────────────────────────────────────────────── */
  {
    id: 25,
    date: "2026-05-04",
    axis: {
      label: "AMAZON REVIEW ←→ POLITICAL SPEECH",
      left_pole: "AMAZON REVIEW",
      right_pole: "POLITICAL SPEECH",
      description: "Both are trying to convince you of something. One has a star rating.",
    },
    artifacts: [
      {
        id: "a",
        text: "This product changed my life. I don't say that lightly. I've tried everything else. This is the one.",
        category: "advertising",
        axis_position: -2,
        highlighted_words: ["changed my life", "tried everything else", "This is the one"],
        reveal: "Consumer testimony operates on personal authority. \"I don't say that lightly\" is the review-writer's version of citing credentials. \"This is the one\" is the messianic claim applied to a blender. It has 847 helpful votes.",
      },
      {
        id: "b",
        text: "Exactly as described. Arrived on time. No complaints. Would purchase again.",
        category: "corporate",
        axis_position: -0.7,
        highlighted_words: ["Exactly as described", "Would purchase again"],
        reveal: "The most under-rated genre of writing: accurate description of an adequate experience. No hyperbole. No narrative. \"Would purchase again\" is the consumer equivalent of a standing ovation — offered quietly, which makes it the most reliable review in the set.",
      },
      {
        id: "c",
        text: "Look, no one has all the answers. But if we listen to each other and stay focused on what we share, I believe we can get there.",
        category: "speech",
        axis_position: 0.8,
        highlighted_words: ["no one has all the answers", "what we share", "I believe"],
        reveal: "\"I believe\" is the hedge that sounds like conviction. \"No one has all the answers\" is the opening that positions the speaker as humble while suggesting they have more answers than the alternative. \"Get there\" remains undefined, which is useful.",
      },
      {
        id: "d",
        text: "This is not just an election. This is the defining moment of our civilization. History will look back and ask: where were you?",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["not just an election", "defining moment", "History will look back"],
        reveal: "The text has been delivered at most elections held in living memory. \"History will look back\" asks you to imagine an audience watching from the future, which is an effective rhetorical technique and also unfalsifiable until you are dead.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 26 ────────────────────────────────────────────────────────────────── */
  {
    id: 26,
    date: "2026-05-05",
    axis: {
      label: "CORPORATE DEI STATEMENT ←→ ACTUAL ALLY",
      left_pole: "CORPORATE DEI",
      right_pole: "ACTUAL ALLY",
      description: "One was written by a committee. One was written by a person who will get in trouble for saying this.",
    },
    artifacts: [
      {
        id: "a",
        text: "We are committed to fostering a diverse, equitable, and inclusive workplace where all voices are heard and valued.",
        category: "corporate",
        axis_position: -2,
        highlighted_words: ["committed to fostering", "diverse, equitable, and inclusive", "all voices are heard and valued"],
        reveal: "\"Fostering\" is a word that means nurturing over time, which is measurable. The statement does not include measurements. \"All voices are heard\" is a claim about listening, not about outcomes. The sentence has a legal team.",
      },
      {
        id: "b",
        text: "Diversity is not a checkbox. We are actively examining our hiring practices, pay gaps, and who gets promoted.",
        category: "corporate",
        axis_position: -0.6,
        highlighted_words: ["not a checkbox", "actively examining", "who gets promoted"],
        reveal: "\"Not a checkbox\" is often the first sentence of a very long checkbox. \"Actively examining\" is more specific than the previous text, which makes it better. The examination has been initiated; the results have not been released, which is where most examinations currently reside.",
      },
      {
        id: "c",
        text: "I had advantages I didn't earn and didn't see until someone pointed them out. I'm still figuring out what to do with that.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["advantages I didn't earn", "didn't see", "still figuring out"],
        reveal: "\"Still figuring out\" is not a resolution — it is an honest account of a process in progress. The admission that the advantages were invisible until pointed out is harder to perform than the admission itself. This sentence was written without a communications team.",
      },
      {
        id: "d",
        text: "I declined the panel. There were no women on it. They asked me to recommend someone. I gave them five names. They found the budget.",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["declined the panel", "five names", "found the budget"],
        reveal: "The text describes actions, not commitments. \"They found the budget\" is the punchline that proves the previous budget was a choice. The speaker does not describe themselves as an ally. The series of short sentences is the structure of someone who has done this before and is not performing it.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 27 ────────────────────────────────────────────────────────────────── */
  {
    id: 27,
    date: "2026-05-06",
    axis: {
      label: "SOUNDS LIKE PROPAGANDA ←→ SOUNDS LIKE ADVERTISING",
      left_pole: "PROPAGANDA",
      right_pole: "ADVERTISING",
      description: "The techniques are the same. The disclaimers differ. One of them is legally required.",
    },
    artifacts: [
      {
        id: "a",
        text: "The enemies of progress are everywhere. They do not want you to succeed. Together, we will not let them win.",
        category: "speech",
        axis_position: -2,
        highlighted_words: ["enemies of progress", "everywhere", "do not want you to succeed", "not let them win"],
        reveal: "The rhetorical structure: name an enemy, attribute motivation, unify against them. The enemy is not described beyond \"enemies of progress,\" which means anyone can be placed in that category. \"Everywhere\" is the word that makes the threat total and the response unlimited.",
      },
      {
        id: "b",
        text: "Our nation's strength comes from its people. From sacrifice. From unity. From the belief that tomorrow is worth fighting for.",
        category: "speech",
        axis_position: -0.7,
        highlighted_words: ["nation's strength", "sacrifice", "unity", "worth fighting for"],
        reveal: "The sentence accumulates abstractions — strength, sacrifice, unity, belief — without attaching them to policy. This is the language of national identification, which can be used for anything from recruiting soldiers to selling insurance. Both have happened.",
      },
      {
        id: "c",
        text: "Nine out of ten dentists recommend this toothpaste. The tenth one hasn't tried it yet.",
        category: "advertising",
        axis_position: 0.9,
        highlighted_words: ["Nine out of ten dentists", "The tenth one"],
        reveal: "The joke in the second sentence is doing something unusual: it acknowledges the sample. This is an ad that is self-aware about being an ad, which makes it the most honest text in this set. The ninety percent is still the headline. The humor is the fine print.",
      },
      {
        id: "d",
        text: "Results may vary. Individual experiences are not representative of typical outcomes. Paid endorsement.",
        category: "advertising",
        axis_position: 2,
        highlighted_words: ["Results may vary", "not representative of typical outcomes", "Paid endorsement"],
        reveal: "This is the legally mandated inverse of every other text in today's set. It is required to tell you that everything before it was a performance. The sentence exists because, in the absence of it, the performance was taken as reality. It still is, for most people.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 28 ────────────────────────────────────────────────────────────────── */
  {
    id: 28,
    date: "2026-05-07",
    axis: {
      label: "MANIFESTO ←→ TERMS OF SERVICE",
      left_pole: "MANIFESTO",
      right_pole: "TERMS OF SERVICE",
      description: "Both describe the conditions under which you are allowed to exist here. One is longer.",
    },
    artifacts: [
      {
        id: "a",
        text: "We declare the current order illegitimate. Its laws protect property. Its prisons protect power. We are building something else.",
        category: "manifesto",
        axis_position: -2,
        highlighted_words: ["declare", "illegitimate", "protect property", "protect power", "something else"],
        reveal: "The two-clause analysis of law and prison is compressed enough to be a slogan and specific enough to be an argument. \"Something else\" is the refusal to name the alternative before it exists — which is either strategic or honest, depending on what comes next.",
      },
      {
        id: "b",
        text: "We hold these truths to be self-evident: that all are created equal, and that governments derive their powers from the consent of the governed.",
        category: "speech",
        axis_position: -0.7,
        highlighted_words: ["self-evident", "created equal", "consent of the governed"],
        reveal: "\"Self-evident\" is a rhetorical move: it declares that the claim requires no proof, which is useful when proof is unavailable. The document asserting universal equality was written by men who owned people. This is the most studied gap in the history of political writing.",
      },
      {
        id: "c",
        text: "By accessing this service, you agree to our Terms of Service, Privacy Policy, and Cookie Policy. We reserve the right to modify these terms at any time.",
        category: "corporate",
        axis_position: 0.9,
        highlighted_words: ["By accessing", "you agree", "reserve the right to modify"],
        reveal: "\"By accessing\" means that arriving at this page constitutes signing a contract. \"We reserve the right to modify at any time\" means the contract you signed may be different by tomorrow. You will be notified by email, which you will not open.",
      },
      {
        id: "d",
        text: "Company may, in its sole discretion, terminate your access immediately and without notice for any reason not prohibited by applicable law.",
        category: "corporate",
        axis_position: 2,
        highlighted_words: ["sole discretion", "immediately and without notice", "any reason"],
        reveal: "\"Sole discretion\" means: we decide. \"Without notice\" means: you will find out afterward. \"Any reason\" means the list of reasons is not a list — it is a posture. This sentence is the Terms of Service at maximum honesty, which is why it appears on page 12.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 29 ────────────────────────────────────────────────────────────────── */
  {
    id: 29,
    date: "2026-05-08",
    axis: {
      label: "GEN Z WROTE THIS ←→ BOOMER GUESSING WHAT GEN Z SAYS",
      left_pole: "GEN Z",
      right_pole: "BOOMER GUESSING",
      description: "One of these was written by someone under 25. The others were written by people trying.",
    },
    artifacts: [
      {
        id: "a",
        text: "It's giving very much 'we need to talk' energy and honestly I'm not built for that conversation today.",
        category: "lyric",
        axis_position: -2,
        highlighted_words: ["It's giving", "energy", "not built for that"],
        reveal: "\"Not built for that\" treats emotional capacity as infrastructure — a limitation of design rather than a failure of will. This reframing is the linguistic signature of a generation that grew up with the vocabulary of mental health. The sentence is also extremely funny.",
      },
      {
        id: "b",
        text: "No cap, this hits different. The vibe is immaculate. Main character behavior, honestly.",
        category: "lyric",
        axis_position: -0.6,
        highlighted_words: ["No cap", "hits different", "Main character"],
        reveal: "The vocabulary is correct but the density is off. No speaker under 30 uses this many markers in a single sentence — it has the quality of a checklist rather than a voice. The phrases are accurate; their arrangement is the tell.",
      },
      {
        id: "c",
        text: "Your vibe is immaculate. Your weekend is valid. Your rest is earned. (Also, our sale ends Sunday.)",
        category: "advertising",
        axis_position: 0.9,
        highlighted_words: ["vibe is immaculate", "weekend is valid", "sale ends Sunday"],
        reveal: "The brand has read the style guide. \"Your weekend is valid\" is therapeutic language borrowed to sell something. The parenthetical — \"(Also, our sale ends Sunday)\" — is the company being self-aware about what it is doing, which is now itself a branding strategy.",
      },
      {
        id: "d",
        text: "Young people today are so resilient. Despite everything, they're out there making a difference. Be very proud of yourselves!",
        category: "speech",
        axis_position: 2,
        highlighted_words: ["Young people today", "Despite everything", "Be very proud"],
        reveal: "\"Despite everything\" is the phrase that acknowledges a problem without describing it. \"Be very proud of yourselves\" is issued as an instruction, which removes its function as recognition. The exclamation point is doing the warmth that the sentence's structure has displaced.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

  /* ── 30 ────────────────────────────────────────────────────────────────── */
  {
    id: 30,
    date: "2026-05-09",
    axis: {
      label: "SOUNDS LIKE THE END ←→ SOUNDS LIKE THE BEGINNING",
      left_pole: "ENDING",
      right_pole: "BEGINNING",
      description: "Context is everything. These four texts are midpoints. You decide which direction they're pointing.",
    },
    artifacts: [
      {
        id: "a",
        text: "After everything, this is what remains: the light through the window, the smell of coffee, the ordinary morning.",
        category: "literary",
        axis_position: -2,
        highlighted_words: ["After everything", "what remains", "ordinary morning"],
        reveal: "\"After everything\" is an ending that doesn't name what was lost. What remains is sensory and small — not because the losses were small but because the small things are what survives them. The ordinary morning is the sentence's answer to whatever the question was.",
      },
      {
        id: "b",
        text: "There's nothing left to prove. Nothing left to win. Just this — the quiet after.",
        category: "literary",
        axis_position: -0.7,
        highlighted_words: ["nothing left to prove", "Nothing left to win", "the quiet after"],
        reveal: "The sentence might be peace or it might be exhaustion — the grammar cannot tell you which. \"The quiet after\" names itself as a sequel, which means something preceded it. The text is standing in a room where something has just happened and choosing to describe the silence.",
      },
      {
        id: "c",
        text: "I stopped waiting for permission. I stopped waiting to be ready. I started.",
        category: "speech",
        axis_position: 0.9,
        highlighted_words: ["stopped waiting for permission", "stopped waiting to be ready", "I started"],
        reveal: "The two \"stoppings\" clear the field for the final verb: \"I started.\" The sentence is a before-and-after where the after is the act of beginning, not the act of completing. The past tense of \"started\" means it is already underway. There is no finish line described.",
      },
      {
        id: "d",
        text: "Everything about to happen has already begun. You just don't know it yet.",
        category: "literary",
        axis_position: 2,
        highlighted_words: ["about to happen", "already begun", "don't know it yet"],
        reveal: "The sentence collapses the distinction between before and during. \"Already begun\" makes the future retroactively present, which is either a statement about causality or a rhetorical strategy for generating anticipation. \"You just don't know it yet\" places the reader inside a story that has already started without them.",
      },
    ],
    correct_order: ["a", "b", "c", "d"],
  },

];

/** Alias for backward compatibility — returns today's challenge */
export const DAILY_UNDERTOW: DailyChallenge = getDailyChallenge();
