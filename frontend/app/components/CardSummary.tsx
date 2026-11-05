import { splitSummaryForCard } from "../lib/utils";

/** A card's summary, shown to its last whole sentence that fits and with the
 *  remainder kept in the page but hidden (see splitSummaryForCard). */
export default function CardSummary({ text, max }: { text: string | null | undefined; max: number }) {
  const [shown, rest] = splitSummaryForCard(text, max);
  return (
    <>
      {shown}
      {rest && <span className="card-summary__rest">{rest}</span>}
    </>
  );
}
