import { IM_Fell_English, Lora, Old_Standard_TT } from "next/font/google";

/* ---------------------------------------------------------------------------
   Paper Edition Layout — Period Font Loading
   Loads IM Fell English, Lora, Old Standard TT for the broadsheet view.
   These fonts only load on /paper routes (not the digital edition).
   --------------------------------------------------------------------------- */

const imFell = IM_Fell_English({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--np-fell",
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
      className={`${imFell.variable} ${lora.variable} ${oldStandard.variable}`}
    >
      {children}
    </div>
  );
}
