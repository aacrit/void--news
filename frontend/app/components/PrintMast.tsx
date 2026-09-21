import SigilWordmark from "./SigilWordmark";
import { SITE_URL } from "../lib/siteMeta";

/* ---------------------------------------------------------------------------
   PrintMast: the masthead a printed page carries.

   On screen the one masthead is mounted by app/layout.tsx and hidden from
   print by app/styles/brand.css, because a sticky navigation bar is screen
   chrome. A sheet still needs to say where it came from, so a long read
   (a Deep Dive, a History event) prints with the wordmark and its own address
   at the top. Display: none until @media print; aria-hidden because on screen
   it does not exist and on paper there is no reader technology to hide from.
   --------------------------------------------------------------------------- */
export default function PrintMast({ path }: { path: string }) {
  const clean = path.startsWith("/") ? path : `/${path}`;
  return (
    <div className="print-mast" aria-hidden="true">
      <SigilWordmark height={22} product="NEWS" />
      <span className="print-mast__url">{`${SITE_URL.replace(/^https?:\/\//, "")}${clean}`}</span>
    </div>
  );
}
