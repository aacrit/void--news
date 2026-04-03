import type { Metadata, Viewport } from "next";
import {
  Playfair_Display,
  Inter,
  IBM_Plex_Mono,
  Barlow_Condensed,
} from "next/font/google";
import { BrandVersionProvider } from "./lib/brandVersion";
import "./globals.css";

/* ---------------------------------------------------------------------------
   Four Voices of Type
   Editorial:  Playfair Display — headlines, story titles, section headers
   Structural: Inter — body text, navigation, labels, buttons
   Meta:       Barlow Condensed — editorial metadata (source counts, categories,
               timestamps, velocity) — condensed grotesque in the Franklin Gothic
               / News Gothic newspaper tradition
   Data:       IBM Plex Mono — bias scores, numeric data, tabular figures —
               humanist mono with institutional warmth (not a coding font)
   --------------------------------------------------------------------------- */

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-playfair",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
  display: "swap",
});

const barlowCondensed = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-barlow",
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-ibm-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://aacrit.github.io"),
  title: "void --news — See every side of the story",
  description:
    "Free news aggregation with per-article bias analysis across 950+ curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
  keywords: [
    "news",
    "bias analysis",
    "media literacy",
    "journalism",
    "political bias",
    "news aggregation",
    "fact checking",
  ],
  authors: [{ name: "void --news" }],
  openGraph: {
    title: "void --news — See every side of the story",
    description:
      "Free news aggregation with per-article bias analysis across 950+ curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
    type: "website",
    siteName: "void --news",
    images: [
      {
        url: "/void--news/og-image.svg",
        width: 1200,
        height: 630,
        alt: "void --news — News aggregation with multi-axis bias analysis",
        type: "image/svg+xml",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "void --news — See every side of the story",
    description:
      "Free news aggregation with per-article bias analysis across 950+ curated sources.",
    images: ["/void--news/twitter-card.svg"],
  },
  icons: {
    icon: [
      { url: "/void--news/icon.svg", type: "image/svg+xml" },
      { url: "/void--news/favicon.ico", sizes: "32x32" },
    ],
    apple: [
      { url: "/void--news/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  manifest: "/void--news/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F0EBDD" },
    { media: "(prefers-color-scheme: dark)", color: "#1C1A17" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      data-mode="dark"
      className={`${playfair.variable} ${inter.variable} ${barlowCondensed.variable} ${ibmPlexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Preconnect to Supabase — eliminates DNS + TLS handshake latency
            on first client-side query (~100-300ms savings on cold load) */}
        <link rel="preconnect" href="https://xryzskhgfuafyotrcdvj.supabase.co" />
        <link rel="dns-prefetch" href="https://xryzskhgfuafyotrcdvj.supabase.co" />
        {/* Fonts loaded via next/font/google above — no additional font loads needed.
            Chomsky, IM Fell English, Old Standard TT, and Lora were removed:
            none are referenced in CSS. Saves 4 network requests. */}
        {/* CSP: restrict script/connect/style/font/img sources */}
        <meta
          httpEquiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://*.supabase.co; media-src 'self' https://*.supabase.co; img-src 'self' data: https://*.google.com https://*.googleapis.com https://*.gstatic.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self';"
        />
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        <meta httpEquiv="Referrer-Policy" content="strict-origin-when-cross-origin" />
        {/* PWA: iOS standalone mode + Android install support */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="mobile-web-app-capable" content="yes" />
        {/* Status bar integration — matches app chrome to warm paper tones */}
        <meta name="theme-color" content="#1C1A17" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#F0EBDD" media="(prefers-color-scheme: light)" />
        {/* Inline script to set theme + brand version before first paint — avoids flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('void-news-theme');
                  if (stored === 'light') {
                    document.documentElement.setAttribute('data-mode', 'light');
                  } else if (!stored && window.matchMedia('(prefers-color-scheme: light)').matches) {
                    document.documentElement.setAttribute('data-mode', 'light');
                  }
                  var brand = localStorage.getItem('void-brand-version');
                  document.documentElement.setAttribute('data-brand', brand === 'v1' ? 'v1' : 'v2');
                } catch(e) {}
              })();
              if ('serviceWorker' in navigator) {
                navigator.serviceWorker.register('/void--news/sw.js').catch(function() {});
              }
            `,
          }}
        />
      </head>
      <body
        style={{
          fontFamily: "var(--font-structural)",
        }}
      >
        {/* Skip to content — accessibility */}
        <a
          href="#main-content"
          className="skip-to-content"
        >
          Skip to main content
        </a>
        <BrandVersionProvider>
          {children}
        </BrandVersionProvider>
      </body>
    </html>
  );
}
