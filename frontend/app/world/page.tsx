import WorldPageContent from "../components/WorldPageContent";

/* ---------------------------------------------------------------------------
   /world — direct route to the World overflow section.

   Same data set as the homepage's inline World section (mobile More menu,
   deep links, social shares hit this URL). Renders ONLY the overflow stories
   that didn't make the top 50, stripped of homepage chrome (lead, brief,
   skybox). The divider doubles as the page's section signal.
   --------------------------------------------------------------------------- */

export const metadata = {
  title: "World — void --news",
  description: "International stories ranked beyond the homepage cut. Same fetched set, overflow only.",
};

export default function WorldPage() {
  return <WorldPageContent />;
}
