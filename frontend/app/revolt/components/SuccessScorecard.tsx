'use client';

import type { Revolution } from '../types';
import { factorCountLabel, successBand, bandClass } from '../scoring';

/* The analytical heart of the active portal. Each factor shows its cited base
   rate BESIDE this movement's dated status. Never merged into a verdict, never
   summed into a probability. The only summary is a descriptive count + a band. */
export default function SuccessScorecard({ revolution: r }: { revolution: Revolution }) {
  const band = successBand(r.successFactors);

  return (
    <section aria-label="Success factor scorecard">
      <h2 className="rev-h2">Weighed against the record</h2>

      <div className="rev-disclaimer">
        Analytical, not predictive. This weighs the movement against scholarly base rates. It is
        not a forecast and not an endorsement.
        {r.analysisReviewedAt && (
          <span className="rev-review-stamp"> &nbsp;Analysis last reviewed: {r.analysisReviewedAt}.</span>
        )}
      </div>

      <p style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
        <span className="rev-count">{factorCountLabel(r.successFactors)}</span>
        {band && <span className={`rev-band ${bandClass(band)}`}>{band}</span>}
      </p>

      <div className="rev-scorecard">
        {r.successFactors.map((f, i) => (
          <div className="rev-factor" key={i}>
            <div className="rev-factor__head">
              <span className="rev-factor__label">{f.label}</span>
              <span className={`rev-factor__dir rev-factor__dir--${f.direction}`}>
                {f.direction === 'favors-movement' ? 'Favors the movement'
                  : f.direction === 'favors-regime' ? 'Favors the regime'
                  : 'Indeterminate'}
              </span>
            </div>
            <p className="rev-factor__baserate">{f.baseRate}</p>
            <p className="rev-factor__status">
              {f.status}
              {f.asOf && <span className="rev-review-stamp"> &nbsp;(as of {f.asOf})</span>}
            </p>
            {f.sources.length > 0 && <p className="rev-factor__src">{f.sources.join('; ')}</p>}
          </div>
        ))}
      </div>
    </section>
  );
}
