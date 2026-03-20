import type { Metadata, Viewport } from "next";
import {
  Playfair_Display,
  Inter,
  JetBrains_Mono,
} from "next/font/google";
import "./globals.css";

/* ---------------------------------------------------------------------------
   Three Voices of Type
   Editorial: Playfair Display — headlines, story titles, section headers
   Structural: Inter — body text, navigation, labels, buttons
   Data: JetBrains Mono — bias scores, source counts, timestamps
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

const jetbrains = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://aacrit.github.io"),
  title: "void --news — See every side of the story",
  description:
    "Free news aggregation with per-article bias analysis across 200 curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
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
      "Free news aggregation with per-article bias analysis across 200 curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
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
      "Free news aggregation with per-article bias analysis across 200 curated sources.",
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
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAF8F5" },
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
      className={`${playfair.variable} ${inter.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Preconnect to Supabase — eliminates DNS + TLS handshake latency
            on first client-side query (~100-300ms savings on cold load) */}
        <link rel="preconnect" href="https://xryzskhgfuafyotrcdvj.supabase.co" />
        <link rel="dns-prefetch" href="https://xryzskhgfuafyotrcdvj.supabase.co" />
        {/* E-paper period fonts — non-blocking load */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Chomsky: open-source blackletter in the style of the NYT nameplate.
            Designed by Fredrick Brennan, OFL license. English Textura tradition —
            upright, elegant, correct stroke weight. Not the heavy Fraktur of
            UnifrakturCook. CDN via Font Library (fontlibrary.org). */}
        <link
          rel="stylesheet"
          href="https://fontlibrary.org//face/chomsky"
          type="text/css"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=IM+Fell+English:ital@0;1&family=Old+Standard+TT:ital,wght@0,400;0,700;1,400&family=Lora:ital,wght@0,400;0,700;1,400;1,700&display=swap"
        />
        {/* Inline script to set theme before first paint — avoids flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('void-news-theme');
                  if (stored === 'light') {
                    document.documentElement.setAttribute('data-mode', 'light');
                  }
                } catch(e) {}
              })();
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
        {children}
      </body>
    </html>
  );
}
