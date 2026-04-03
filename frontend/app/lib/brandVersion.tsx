"use client";

/* ---------------------------------------------------------------------------
   Brand Version Context — Toggle between V1 (scale beam) and V2 (void lens)

   V1: Original hybrid icon — void circle + scale beam + post + base
   V2: Void Lens — the void circle IS the entire mark, lean encoded via
       asymmetric stroke weight around the perimeter

   Stored in localStorage("void-brand-version"). Default: "v2".
   Sets data-brand attribute on <html> for CSS-level branching.
   --------------------------------------------------------------------------- */

import { createContext, useContext, useState, useEffect, useCallback } from "react";

type BrandVersion = "v1" | "v2";

const BrandVersionContext = createContext<{
  version: BrandVersion;
  setVersion: (v: BrandVersion) => void;
}>({ version: "v2", setVersion: () => {} });

export function BrandVersionProvider({ children }: { children: React.ReactNode }) {
  const [version, setVersionState] = useState<BrandVersion>("v2");

  useEffect(() => {
    const stored = localStorage.getItem("void-brand-version") as BrandVersion | null;
    if (stored === "v1" || stored === "v2") {
      setVersionState(stored);
      document.documentElement.setAttribute("data-brand", stored);
    } else {
      document.documentElement.setAttribute("data-brand", "v2");
    }
  }, []);

  const setVersion = useCallback((v: BrandVersion) => {
    setVersionState(v);
    localStorage.setItem("void-brand-version", v);
    document.documentElement.setAttribute("data-brand", v);
  }, []);

  return (
    <BrandVersionContext.Provider value={{ version, setVersion }}>
      {children}
    </BrandVersionContext.Provider>
  );
}

export function useBrandVersion() {
  return useContext(BrandVersionContext);
}
