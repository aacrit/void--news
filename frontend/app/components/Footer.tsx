"use client";

import { GithubLogo } from "@phosphor-icons/react";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   --------------------------------------------------------------------------- */

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <div className="footer-masthead">
          <ScaleIcon animation="idle" size={20} />
          void <span className="footer-masthead__code">--news</span>
        </div>
        <p className="footer-tagline">Free, transparent news bias analysis</p>
        <p className="footer-stats">90 curated sources &middot; Updated twice daily</p>
        <a
          href="https://github.com/aacrit/void-news"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View source on GitHub"
          className="footer-github"
        >
          <GithubLogo size={16} weight="light" aria-hidden="true" />
          Source
        </a>
        <p className="footer-built">Built with transparency in mind</p>
      </div>
    </footer>
  );
}
