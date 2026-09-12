import type { IgPostRow } from "../../lib/supabase-server";

export function PostedRow({ row }: { row: IgPostRow }) {
  const m = row.metrics ?? {};
  const get = (k: string) => (m as Record<string, number | undefined>)[k] ?? 0;
  return (
    <div className="ig-posted">
      <div className="ig-posted__thumb">
        {row.image_urls?.[0] && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={row.image_urls[0]} alt="" />
        )}
      </div>
      <div className="ig-posted__body">
        <div className="ig-posted__meta">
          <span className="ig-review__pill" data-pillar={row.pillar}>
            {row.pillar}
          </span>
          <span className="ig-posted__when">
            {row.posted_at ? new Date(row.posted_at).toLocaleString() : "n/a"}
          </span>
          {row.ig_permalink && (
            <a href={row.ig_permalink} target="_blank" rel="noopener">
              open on instagram →
            </a>
          )}
          {row.bluesky_uri && (
            <span className="ig-posted__when">· cross-posted to bluesky</span>
          )}
        </div>
        <p className="ig-posted__caption">{row.caption?.slice(0, 240)}</p>
        <div className="ig-posted__metrics">
          <span>reach {get("reach")}</span>
          <span>saved {get("saved")}</span>
          <span>shares {get("shares")}</span>
          <span>profile_visits {get("profile_visits")}</span>
          <span>website_clicks {get("website_clicks")}</span>
        </div>
      </div>
    </div>
  );
}
