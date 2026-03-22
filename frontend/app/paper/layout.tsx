import {
  Playfair_Display,
  Inter,
  JetBrains_Mono,
} from "next/font/google";

/* ---------------------------------------------------------------------------
   Paper Edition Layout — Reuses Three Voices from the digital edition.
   No extra font downloads. Brand continuity.
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

export default function PaperLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className={`${playfair.variable} ${inter.variable} ${jetbrains.variable}`}
    >
      {children}
    </div>
  );
}
