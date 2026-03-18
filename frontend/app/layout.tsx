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
  title: "void --news",
  description:
    "News aggregation with multi-dimensional bias analysis. See the full picture.",
  keywords: ["news", "bias analysis", "media literacy", "journalism"],
  authors: [{ name: "void --news" }],
  openGraph: {
    title: "void --news",
    description:
      "News aggregation with multi-dimensional bias analysis. See the full picture.",
    type: "website",
  },
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
        {children}
      </body>
    </html>
  );
}
