/**
 * Returns "Morning" or "Evening" based on the edition's regional time zone.
 * US → America/New_York, India → Asia/Kolkata, World → UTC.
 */
export function getEditionTimeOfDay(edition: string): "Morning" | "Evening" {
  const now = new Date();
  let hour: number;

  if (edition === "us") {
    hour = parseInt(
      now.toLocaleString("en-US", {
        hour: "numeric",
        hour12: false,
        timeZone: "America/New_York",
      }),
      10,
    );
  } else if (edition === "india") {
    hour = parseInt(
      now.toLocaleString("en-US", {
        hour: "numeric",
        hour12: false,
        timeZone: "Asia/Kolkata",
      }),
      10,
    );
  } else {
    // World edition — UTC
    hour = now.getUTCHours();
  }

  return hour < 12 ? "Morning" : "Evening";
}

/**
 * Returns a compact regional timestamp string for the dateline.
 * US: "9 AM ET"  World: "14:05 UTC"  India: "19:35 IST"
 */
export function getEditionTimestamp(edition: string): string {
  const now = new Date();

  if (edition === "us") {
    const et = now
      .toLocaleString("en-US", {
        hour: "numeric",
        hour12: true,
        timeZone: "America/New_York",
      })
      .replace(" AM", " AM")
      .replace(" PM", " PM");
    return `${et} ET`;
  } else if (edition === "india") {
    const ist = now.toLocaleString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: false,
      timeZone: "Asia/Kolkata",
    });
    return `${ist} IST`;
  } else {
    const h = String(now.getUTCHours()).padStart(2, "0");
    const m = String(now.getUTCMinutes()).padStart(2, "0");
    return `${h}:${m} UTC`;
  }
}

/**
 * Relative time formatting — "5m ago", "2h ago", "1d ago"
 */
export function timeAgo(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

/**
 * Derive "Why This Story" ranking explanation from available story data.
 * Returns the top 2-3 signals that drove this story's ranking.
 */
export function whyThisStory(opts: {
  sourceCount: number;
  coverageVelocity: number;
  divergenceScore: number;
  leanSpread?: number;
  headlineRank: number;
}): string[] {
  const reasons: { text: string; weight: number }[] = [];

  if (opts.sourceCount >= 8) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 90 });
  } else if (opts.sourceCount >= 5) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 70 });
  } else if (opts.sourceCount >= 3) {
    reasons.push({ text: `${opts.sourceCount} sources`, weight: 40 });
  }

  if (opts.coverageVelocity >= 5) {
    reasons.push({ text: "Rapidly developing", weight: 85 });
  } else if (opts.coverageVelocity >= 3) {
    reasons.push({ text: "Gaining coverage", weight: 55 });
  }

  if (opts.divergenceScore >= 60) {
    reasons.push({ text: "High source disagreement", weight: 75 });
  } else if (opts.divergenceScore >= 30) {
    reasons.push({ text: "Sources differ on framing", weight: 45 });
  }

  if (opts.leanSpread != null && opts.leanSpread >= 20) {
    reasons.push({ text: "Cross-spectrum coverage", weight: 65 });
  }

  // Sort by weight descending, take top 3
  reasons.sort((a, b) => b.weight - a.weight);
  return reasons.slice(0, 3).map((r) => r.text);
}
