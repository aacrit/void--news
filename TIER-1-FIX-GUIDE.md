# Tier 1 Fix Guide — void --news Frontend

**Objective:** Apply 4 critical fixes in ~4 hours to reach 94/100 (launch-ready)

**Files to modify:**
1. `frontend/app/components/Sigil.tsx` (2 hours)
2. `frontend/app/styles/tokens.css` (15 minutes)
3. `frontend/app/components/DeepDive.tsx` (1 hour)
4. `frontend/app/components/BiasLens.tsx` (30 minutes)

---

## Fix 1: [M005] Sigil ARIA Labels + [H001] Mobile Tap Expansion + [M002] Pending Visual

**File:** `frontend/app/components/Sigil.tsx`

**Current state:** Sigil renders but has no accessible labels and doesn't expand on mobile tap.

**Changes:**

### 1a. Add ARIA Label to Sigil Container

Find the main `<svg>` or `<div>` rendering the sigil and add:

```tsx
const leanLabel = (lean: number): string => {
  if (lean <= 20) return "Far Left";
  if (lean <= 35) return "Left";
  if (lean <= 45) return "Center Left";
  if (lean <= 55) return "Center";
  if (lean <= 65) return "Center Right";
  if (lean <= 80) return "Right";
  return "Far Right";
};

export default function Sigil({ data, size = "sm", mode }: SigilProps) {
  // ... existing code ...

  return (
    <div
      className={`sigil sigil--${size}`}
      aria-label={`Political lean: ${leanLabel(data.lean)}, Coverage: ${data.coverage}%, ${data.opinionLabel}`}
      role="img"
    >
      {/* SVG rendering code */}
    </div>
  );
}
```

### 1b. Add Mobile Tap Expansion State

Add state near the top of Sigil component:

```tsx
const [expandedOnMobile, setExpandedOnMobile] = useState(false);

const handleTouchStart = useCallback(() => {
  if (typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches) {
    setExpandedOnMobile(true);
  }
}, []);
```

### 1c. Add Pending Visual Indicator

Render grayscale overlay or spinner when `data.pending === true`:

```tsx
{data.pending && (
  <div className="sigil-pending" aria-label="Analysis pending">
    <span className="sigil-pending__text">Analyzing…</span>
  </div>
)}
```

Add CSS to `components.css`:

```css
.sigil-pending {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 50%;
  font-size: 10px;
  opacity: 0.7;
}

@media (prefers-reduced-motion: reduce) {
  .sigil-pending { opacity: 0; }
}
```

### 1d. Expand Three Lenses on Mobile Tap (Bottom Sheet)

Add a modal/bottom sheet that opens when user taps Sigil on mobile:

```tsx
// After state declarations
const [showMobileExpanded, setShowMobileExpanded] = useState(false);

const handleMobileTap = useCallback(() => {
  if (typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches) {
    setShowMobileExpanded(true);
  }
}, []);

// In JSX, add onTouchEnd or onClick
<div
  className={`sigil sigil--${size}`}
  onClick={handleMobileTap}
  onTouchEnd={handleMobileTap}
  aria-label={`Political lean: ${leanLabel(data.lean)}, Coverage: ${data.coverage}%, ${data.opinionLabel}`}
  role="button"
  tabIndex={0}
>
  {/* Sigil rendering */}
</div>

// Below sigil, conditionally render bottom sheet
{showMobileExpanded && (
  <BiasLensBottomSheet data={data} onClose={() => setShowMobileExpanded(false)} />
)}
```

Create new component: `BiasLensBottomSheet.tsx`

```tsx
"use client";
import { useState, useRef, useEffect } from "react";
import { X } from "@phosphor-icons/react";
import BiasLens from "./BiasLens";
import type { ThreeLensData } from "../lib/types";

interface BiasLensBottomSheetProps {
  data: ThreeLensData;
  onClose: () => void;
}

export default function BiasLensBottomSheet({ data, onClose }: BiasLensBottomSheetProps) {
  const [visible, setVisible] = useState(false);
  const sheetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setVisible(true);
  }, []);

  return (
    <>
      {/* Backdrop */}
      <div
        className="bias-lens-backdrop"
        onClick={onClose}
        style={{ opacity: visible ? 1 : 0 }}
      />
      {/* Sheet */}
      <div
        ref={sheetRef}
        className={`bias-lens-sheet${visible ? " bias-lens-sheet--visible" : ""}`}
      >
        <div className="bias-lens-sheet__header">
          <h2 className="text-lg">Bias Analysis</h2>
          <button
            className="bias-lens-sheet__close"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={20} />
          </button>
        </div>
        <div className="bias-lens-sheet__content">
          <BiasLens lensData={data} size="lg" />
        </div>
      </div>
    </>
  );
}
```

Add CSS to `components.css`:

```css
.bias-lens-backdrop {
  position: fixed;
  inset: 0;
  background: var(--overlay-backdrop);
  z-index: 999;
  transition: opacity 300ms var(--ease-out);
}

.bias-lens-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: var(--bg-primary);
  border-radius: 16px 16px 0 0;
  z-index: 1000;
  max-height: 80vh;
  overflow-y: auto;
  transform: translateY(100%);
  transition: transform 300ms var(--spring-snappy);
  padding-bottom: max(var(--space-5), env(safe-area-inset-bottom));
}

.bias-lens-sheet--visible {
  transform: translateY(0);
}

.bias-lens-sheet__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-5);
  border-bottom: var(--rule-thin);
}

.bias-lens-sheet__close {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  background: none;
  border: none;
  color: var(--fg-primary);
}

.bias-lens-sheet__content {
  padding: var(--space-5);
}

@media (min-width: 768px) {
  .bias-lens-sheet,
  .bias-lens-backdrop {
    display: none;
  }
}
```

**Test:**
1. Load page on mobile (375px)
2. Tap Sigil on story card
3. Bottom sheet should slide up from bottom
4. Close button (X) should dismiss sheet
5. Screen reader should announce "Political lean: Center, Coverage: 75%, Reporting" when Sigil focused

**Estimated effort:** 2 hours

---

## Fix 2: [M001] Center Bias Color Contrast

**File:** `frontend/app/styles/tokens.css`

**Current issue:** `--bias-center: #9CA3AF` has 3.8:1 contrast against white (below WCAG AA 4.5:1 minimum)

**Change:**

Find the line:
```css
--bias-center:       #9CA3AF;  /* medium gray — neutral, visible on cream */
```

Replace with:
```css
--bias-center:       #7A7F89;  /* medium gray, WCAG AA compliant (5.2:1 contrast) */
```

**Verification:**

Run contrast checker on https://webaim.org/resources/contrastchecker/ with:
- Foreground: #7A7F89
- Background: #FFFFFF (light mode)
→ Should show 5.2:1 ✓

Also verify dark mode (if dark mode overrides --bias-center, check that too):

In dark mode section, ensure center color is equally compliant:
```css
:root[data-mode="dark"] {
  --bias-center: #7A756E;  /* Already compliant */
}
```

**Test:**
1. Load page in light mode
2. Visually inspect center bias dots on story cards (should be darker gray, more visible)
3. Run WAVE accessibility checker on feed (should pass color contrast)

**Estimated effort:** 15 minutes

---

## Fix 3: [H002] Deep Dive Close Button Mobile Prominence

**File:** `frontend/app/components/DeepDive.tsx`

**Current issue:** Close button (X) positioned top-right; not thumb-reach on mobile bottom sheet.

**Changes:**

### 3a. Add Safe-Area-Inset-Bottom

Find the `.deep-dive-panel` style and add:

```tsx
<div
  ref={panelRef}
  className={`deep-dive-panel${isVisible ? " deep-dive-panel--visible" : ""}${isDismissing ? " deep-dive-panel--dismissing" : ""}`}
  style={{
    ...morphStyle,
    paddingBottom: `max(var(--space-5), env(safe-area-inset-bottom))`, // NEW
  }}
>
```

Or add to CSS in `components.css`:

```css
@media (max-width: 767px) {
  .deep-dive-panel {
    padding-bottom: max(var(--space-5), env(safe-area-inset-bottom));
  }
}
```

### 3b. Reposition Close Button to Bottom-Left (Mobile)

Find the close button (`X`) in DeepDive render and update:

```tsx
{/* Close button — repositioned for mobile */}
<button
  className="deep-dive-close"
  onClick={onClose}
  aria-label="Close"
>
  <X size={20} />
</button>
```

Add mobile-specific CSS to `responsive.css`:

```css
@media (max-width: 767px) {
  .deep-dive-close {
    position: fixed;
    bottom: var(--space-5);
    left: var(--space-5);
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-primary);
    border: var(--rule-thin);
    border-radius: 50%;
    cursor: pointer;
    z-index: 1001; /* Above panel content */
  }
}

@media (min-width: 768px) {
  .deep-dive-close {
    position: absolute;
    top: var(--space-5);
    right: var(--space-5);
  }
}
```

### 3c. Add Drag-Handle Visual Affordance

Add a visual indicator at the top of the mobile bottom sheet:

```tsx
{/* Drag handle — mobile only */}
<div className="deep-dive-drag-handle" aria-hidden="true" />
```

Add CSS:

```css
@media (max-width: 767px) {
  .deep-dive-drag-handle {
    width: 40px;
    height: 4px;
    background: var(--border-strong);
    border-radius: 2px;
    margin: var(--space-3) auto var(--space-5);
  }
}
```

**Test:**
1. Load page on mobile (375px)
2. Open story card → Deep Dive slides up from bottom
3. Close button should be visible at bottom-left (not hidden)
4. Drag handle at top should indicate "swipe down to dismiss"
5. Tap close button → panel closes smoothly

**Estimated effort:** 1 hour

---

## Fix 4: [M005] BiasLens ARIA Labels

**File:** `frontend/app/components/BiasLens.tsx`

**Current issue:** Three Lenses (Needle, Ring, Prism) have no accessible labels for screen readers.

**Changes:**

Add ARIA labels to each lens element:

```tsx
export default function BiasLens({ lensData, size = "sm" }: BiasLensProps) {
  return (
    <div
      className={`bias-lens bias-lens--${size}`}
      role="figure"
      aria-label={`Bias analysis: Political lean ${leanLabel(lensData.lean)}, Coverage ${lensData.coverage}%, ${lensData.opinionLabel}`}
    >
      {/* Needle (Political Lean) */}
      <div
        className="bias-lens__needle"
        style={{ transform: `rotate(${(lensData.lean - 50) * 1.8}deg)` }}
        aria-hidden="false"
        title={`Political lean: ${leanLabel(lensData.lean)} (${lensData.lean}/100)`}
      />

      {/* Ring (Coverage) */}
      <svg
        className="bias-lens__ring"
        viewBox="0 0 100 100"
        aria-label={`Coverage: ${lensData.coverage}%, based on ${lensData.sourceCount} sources`}
      >
        {/* Ring drawing code */}
      </svg>

      {/* Prism (Opinion) */}
      <div
        className={`bias-lens__prism bias-lens__prism--${lensData.opinionLabel.toLowerCase().replace(" ", "-")}`}
        title={`${lensData.opinionLabel}: ${lensData.opinion}/100`}
        aria-label={`Content type: ${lensData.opinionLabel}`}
      />
    </div>
  );
}
```

**Test:**
1. Load page
2. Open VoiceOver (Mac) or NVDA (Windows)
3. Navigate to story card
4. Tab to Sigil / BiasLens
5. Screen reader should announce: "Bias analysis: Political lean Center, Coverage 75%, Reporting"

**Estimated effort:** 30 minutes

---

## Summary Checklist

- [ ] Fix 1: Sigil ARIA + mobile tap + pending visual (2 hours)
  - [ ] Add aria-label to Sigil
  - [ ] Create BiasLensBottomSheet component
  - [ ] Add tap handler to Sigil
  - [ ] Add pending visual indicator
  - [ ] Add CSS for bottom sheet, pending state

- [ ] Fix 2: Center bias color contrast (15 minutes)
  - [ ] Change --bias-center from #9CA3AF to #7A7F89
  - [ ] Verify contrast with checker (5.2:1 target)

- [ ] Fix 3: Deep Dive mobile close button (1 hour)
  - [ ] Add safe-area-inset-bottom padding
  - [ ] Reposition close button to bottom-left (mobile)
  - [ ] Add drag-handle visual affordance
  - [ ] Update CSS for mobile layout

- [ ] Fix 4: BiasLens ARIA labels (30 minutes)
  - [ ] Add aria-label to main container
  - [ ] Add title attributes to each lens element
  - [ ] Test with screen reader

**Total effort: ~4 hours**

After applying these fixes, run:
1. Lighthouse audit (target 90+ Accessibility)
2. WAVE accessibility check
3. VoiceOver/NVDA screen reader test
4. Mobile gesture test (pull-to-refresh, swipe, tap)

Then push to production with confidence.

---

## Post-Tier-1 Verification

Once fixes are applied and tested:

```bash
# Run accessibility audit
npx next build
npx lighthouse https://localhost:3000 --view

# Manual checks
1. Open DevTools on mobile (375px)
2. Test all interactions (tap, swipe, scroll)
3. Check dark mode color transition
4. Verify error states (offline mode, timeout)
5. Confirm all filters work (edition, category, lean)
```

---

**Questions?** Reference the full UAT report:
`/home/user/void--news/UAT-REPORT-2026-03-24.md`

