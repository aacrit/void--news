"use client";

import { useState, useTransition } from "react";
import type { IgPostRow } from "../../lib/supabase-server";
import { approveAction, rejectAction, saveCaptionAction } from "./actions";

interface Props {
  row: IgPostRow;
}

export function ReviewCard({ row }: Props) {
  const [slide, setSlide] = useState(0);
  const [caption, setCaption] = useState(row.caption ?? "");
  const [hashtags, setHashtags] = useState((row.hashtags ?? []).join(" "));
  const [msg, setMsg] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const imageUrls = row.image_urls ?? [];
  const slideCount = imageUrls.length || (row.slide_specs?.length ?? 0);
  const wordCount = caption.trim() ? caption.trim().split(/\s+/).length : 0;

  function call(fn: () => Promise<{ ok: boolean; error?: string }>) {
    startTransition(async () => {
      setMsg(null);
      const r = await fn();
      if (r.ok) {
        setMsg("ok — reload to refresh list");
      } else {
        setMsg(`error: ${r.error ?? "unknown"}`);
      }
    });
  }

  return (
    <article className="ig-review">
      <div className="ig-review__preview">
        {imageUrls[slide] ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrls[slide]}
            alt={`slide ${slide + 1} of ${slideCount}`}
            className="ig-review__img"
          />
        ) : (
          <div className="ig-review__pending">
            no image yet · state: <strong>{row.state}</strong>
            <a
              href={`/ig/render/${row.id}?slide=${slide}`}
              target="_blank"
              rel="noopener"
              className="ig-review__link"
            >
              preview live render →
            </a>
          </div>
        )}
        {slideCount > 1 && (
          <div className="ig-review__slide-strip">
            {Array.from({ length: slideCount }, (_, i) => (
              <button
                key={i}
                className="ig-review__slide-dot"
                aria-current={i === slide}
                onClick={() => setSlide(i)}
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="ig-review__body">
        <div className="ig-review__meta">
          <span className="ig-review__pill" data-pillar={row.pillar}>
            {row.pillar}
          </span>
          <span className="ig-review__pill" data-state={row.state}>
            {row.state}
          </span>
          {row.launch_slot && (
            <span className="ig-review__pill" data-launch="true">
              launch #{row.launch_slot}
            </span>
          )}
          <span className="ig-review__when">
            {new Date(row.scheduled_for).toLocaleString()}
          </span>
        </div>

        <label className="ig-review__label">
          caption{" "}
          <span className="ig-review__meta-inline">
            {wordCount} words · {caption.length} chars
          </span>
        </label>
        <textarea
          className="ig-review__caption"
          value={caption}
          onChange={(e) => setCaption(e.target.value)}
          rows={10}
        />

        <label className="ig-review__label">
          hashtags <span className="ig-review__meta-inline">space-separated, 6 to 8</span>
        </label>
        <input
          className="ig-review__hashtags"
          value={hashtags}
          onChange={(e) => setHashtags(e.target.value)}
        />

        {row.error && (
          <p className="ig-review__error">last error: {row.error}</p>
        )}

        <div className="ig-review__actions">
          <button
            disabled={isPending}
            onClick={() =>
              call(() =>
                saveCaptionAction(
                  row.id,
                  caption,
                  hashtags
                    .split(/\s+/)
                    .map((h) => h.replace(/^#/, ""))
                    .filter(Boolean),
                ),
              )
            }
          >
            save caption
          </button>
          <button
            disabled={isPending || !row.image_urls?.length || !caption.trim()}
            onClick={() => call(() => approveAction(row.id))}
          >
            approve
          </button>
          <button
            disabled={isPending}
            onClick={() => call(() => rejectAction(row.id))}
            className="ig-review__danger"
          >
            reject
          </button>
        </div>

        {msg && <p className="ig-review__msg">{msg}</p>}
      </div>
    </article>
  );
}
