import { Playfair_Display, Lora, Old_Standard_TT } from "next/font/google";

/* ---------------------------------------------------------------------------
   Paper Edition Layout — 1969 NYT Font Loading
   Playfair Display (Cheltenham-like headlines), Lora (body), Old Standard TT (labels).
   --------------------------------------------------------------------------- */

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--np-playfair",
  display: "swap",
});

const lora = Lora({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--np-lora",
  display: "swap",
});

const oldStandard = Old_Standard_TT({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--np-oldstandard",
  display: "swap",
});

export default function PaperLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div
      className={`${playfair.variable} ${lora.variable} ${oldStandard.variable}`}
    >
      {children}
    </div>
  );
}
