import { Lora, Old_Standard_TT } from "next/font/google";

/* ---------------------------------------------------------------------------
   Paper Edition Layout — 1970s NYT Typography
   Loads Lora (body) and Old Standard TT (deck heads).
   Playfair Display (headlines) and Inter (labels) cascade from root layout.
   --------------------------------------------------------------------------- */

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
    <div className={`${lora.variable} ${oldStandard.variable}`}>
      {children}
    </div>
  );
}
