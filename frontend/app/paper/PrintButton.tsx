"use client";

/* The only interactive element on Paper. Hands the page to the browser's own
   print dialog, which is where "Save as PDF" lives; nothing is rendered or
   uploaded server-side. */
export default function PrintButton() {
  return (
    <div className="np-pdf-action">
      <button
        type="button"
        className="np-pdf-btn"
        onClick={() => window.print()}
      >
        Print or save as PDF
      </button>
    </div>
  );
}
