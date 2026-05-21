/* ---------------------------------------------------------------------------
   WorldDivider — section break between US-primary feed and World overflow.

   Visual treatment:
     • Type lockup: "WORLD" in Playfair Display, centered, semantic <h2>
     • Hairlines either side of the word, drawn via ::before/::after on rule

   Newspapers don't explain their sections. The "WORLD" type is the entire
   signal — no count, no caption, no apology. Per CEO 2026-05-15: the
   explicit "didn't make the homepage cut" framing felt meta and
   apologetic; removed in favor of confident silence.

   `count` is accepted for upstream callers but not rendered (kept on the
   prop to avoid breaking imports — can be removed in a future cleanup).
   --------------------------------------------------------------------------- */

interface WorldDividerProps {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  count?: number;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export default function WorldDivider(_props: WorldDividerProps) {
  return (
    <div className="world-divider" role="presentation">
      <div className="world-divider__rule" aria-hidden="true">
        <h2 className="world-divider__type">World</h2>
      </div>
    </div>
  );
}
