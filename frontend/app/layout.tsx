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
  title: "void --news — See every side of the story",
  description:
    "Free news aggregation with per-article bias analysis across 90 curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
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
      "Free news aggregation with per-article bias analysis across 90 curated sources. See political lean, sensationalism, factual rigor, and framing for every story.",
    type: "website",
    siteName: "void --news",
  },
  twitter: {
    card: "summary_large_image",
    title: "void --news — See every side of the story",
    description:
      "Free news aggregation with per-article bias analysis across 90 curated sources.",
  },
  icons: {
    icon: "/void--news/favicon.ico",
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
      data-mode="light"
      className={`${playfair.variable} ${inter.variable} ${jetbrains.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Inline script to set theme before first paint — avoids flash */}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              (function() {
                try {
                  var stored = localStorage.getItem('void-news-theme');
                  if (stored === 'dark' || stored === 'light') {
                    document.documentElement.setAttribute('data-mode', stored);
                  } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                    document.documentElement.setAttribute('data-mode', 'dark');
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
