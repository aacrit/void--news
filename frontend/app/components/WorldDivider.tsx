/* ---------------------------------------------------------------------------
   WorldDivider — section break between US-primary feed and World overflow.

   Visual treatment per 2026-05-15 redesign §6.C2:
     • Type lockup: "WORLD" in Playfair Display, centered, semantic <h2>
     • Hairlines either side of the word, drawn via ::before/::after on rule
     • Caption: "{count} international stories that didn't make the cut"

   The divider IS the signal — no globe icon, no badges, no decoration.
   --------------------------------------------------------------------------- */

interface WorldDividerProps {
  count: number;
}

export default function WorldDivider({ count }: WorldDividerProps) {
  return (
    <div className="world-divider" role="presentation">
      <div className="world-divider__rule" aria-hidden="true">
        <h2 className="world-divider__type">World</h2>
      </div>
      <p className="world-divider__caption">
        {count} international {count === 1 ? "story" : "stories"} that didn&rsquo;t make the homepage cut
      </p>
    </div>
  );
}
