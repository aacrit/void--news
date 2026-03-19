import { test, expect } from "@playwright/test";

/*
  ============================================================================
  UAT — Mobile-Focused Testing for void --news
  Testing at 375px, 390px, 414px (mobile breakpoints)
  ============================================================================

  Critical checks:
  1. Horizontal overflow (no scrollbar at 375px)
  2. NavBar layout (logo + toggle fit, bottom nav visible)
  3. Lead story headline (fits without truncation/overflow)
  4. Story cards (headlines wrap, footer fits in one row)
  5. Filter bar (chips scroll, fade gradient)
  6. Deep Dive panel (full-screen on mobile)
  7. Footer (all content visible, no horizontal overflow)
  8. BiasLens SVGs (fit within cards, popups stay in viewport)
  9. Typography (clamp() values readable)
  10. Touch targets (44x44px minimum)
*/

const MOBILE_WIDTHS = [375, 390, 414];
const MOBILE_HEIGHT = 812;
const LIVE_URL = "https://aacrit.github.io/void--news/";
const LOCAL_URL = "http://localhost:3000";

test.describe("Mobile UAT — Horizontal Overflow & Layout", () => {
  // Test both live deployed and local
  const urls = [
    { name: "live", url: LIVE_URL },
    { name: "local", url: LOCAL_URL, skipIfOffline: true },
  ];

  urls.forEach((urlConfig) => {
    test.describe(`${urlConfig.name} site`, () => {
      MOBILE_WIDTHS.forEach((width) => {
        test(`should have no horizontal scrollbar at ${width}px`, async ({
          browser,
        }) => {
          const context = await browser.newContext({
            viewport: { width, height: MOBILE_HEIGHT },
          });
          const page = await context.newPage();

          try {
            await page.goto(urlConfig.url, { waitUntil: "networkidle" });
          } catch (e) {
            if (urlConfig.skipIfOffline) {
              test.skip();
            } else {
              throw e;
            }
          }

          // Wait for content to load
          await page.waitForTimeout(1000);

          // Check for horizontal scrollbar
          const scrollWidth = await page.evaluate(() => document.documentElement.scrollWidth);
          const clientWidth = await page.evaluate(() => document.documentElement.clientWidth);

          if (scrollWidth > clientWidth) {
            throw new Error(
              `[CRITICAL] Horizontal overflow at ${width}px: scrollWidth=${scrollWidth}, clientWidth=${clientWidth}, overflow=${scrollWidth - clientWidth}px`
            );
          }

          expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
          await context.close();
        });
      });

      // 375px: Most strict mobile testing
      test(`[375px] NavBar fits without overflow`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForTimeout(1000);

        // Check nav-header doesn't overflow
        const navHeader = page.locator(".nav-header");
        const navBox = await navHeader.boundingBox();

        if (navBox) {
          if (navBox.width > 375) {
            throw new Error(
              `[HIGH] NavBar width exceeds 375px: ${navBox.width}px`
            );
          }
        }

        // Check logo is visible
        const navLogo = page.locator(".nav-logo-mobile");
        const isVisible = await navLogo.isVisible();

        if (!isVisible) {
          console.warn("[INFO] Mobile logo not visible at 375px");
        }

        // Check theme toggle is visible
        const themeToggle = page.locator(".theme-toggle");
        const toggleVisible = await themeToggle.isVisible();

        if (!toggleVisible) {
          console.warn("[INFO] Theme toggle not visible at 375px");
        }

        // Bottom nav should be visible at 375px
        const bottomNav = page.locator(".nav-bottom");
        const bottomNavVisible = await bottomNav.isVisible();

        expect(bottomNavVisible).toBe(true);

        await context.close();
      });

      // 375px: Lead story headline
      test(`[375px] Lead story headline fits without overflow`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".lead-story__headline", { timeout: 5000 });

        const headline = page.locator(".lead-story__headline");
        const box = await headline.boundingBox();

        if (box) {
          // Account for padding
          const maxWidth = 375 - 32; // --space-7 padding = 2rem = ~32px on mobile
          if (box.width > maxWidth) {
            throw new Error(
              `[CRITICAL] Lead story headline exceeds ${maxWidth}px: ${box.width}px`
            );
          }
        }

        // Check the max-width: 66% override is NOT applied on mobile
        const maxWidthStyle = await headline.evaluate(
          (el) => window.getComputedStyle(el).maxWidth
        );

        // Should be full width or constrained by parent, not 66%
        expect(maxWidthStyle).not.toBe("247.5px"); // 66% of 375

        await context.close();
      });

      // 375px: Story card footer fits in one row
      test(`[375px] Story card footer fits in one row`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".story-card__footer", { timeout: 5000 });

        const footers = page.locator(".story-card__footer");
        const count = await footers.count();

        if (count === 0) {
          console.warn("[INFO] No story cards found");
          await context.close();
          return;
        }

        // Check first few footers
        for (let i = 0; i < Math.min(count, 3); i++) {
          const footer = footers.nth(i);
          const box = await footer.boundingBox();

          if (box) {
            // Footer should not wrap (single row)
            if (box.height > 50) {
              // 44px min + padding
              throw new Error(
                `[HIGH] Story card footer wrapped (height=${box.height}px) at index ${i}`
              );
            }
          }
        }

        await context.close();
      });

      // 375px: Filter bar horizontal scroll
      test(`[375px] Filter bar scrolls horizontally (no overflow)`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".filter-bar", { timeout: 5000 });

        const filterBar = page.locator(".filter-bar");
        const exists = await filterBar.isVisible();

        if (!exists) {
          console.warn("[INFO] Filter bar not found");
          await context.close();
          return;
        }

        // Check that chips are not wrapping
        const chips = filterBar.locator(".filter-chip");
        const chipCount = await chips.count();

        if (chipCount > 0) {
          const firstChip = chips.first();
          const lastChip = chips.last();

          const firstBox = await firstChip.boundingBox();
          const lastBox = await lastChip.boundingBox();

          if (firstBox && lastBox) {
            // If on the same line, last chip should be to the right of first
            // If wrapped, last chip would be below or same Y
            if (lastBox.y > firstBox.y + 50) {
              throw new Error(
                `[HIGH] Filter chips are wrapping on mobile (${chipCount} chips at ${width}px)`
              );
            }
          }
        }

        // Check fade gradient is visible (::after pseudo)
        const gradientVisible = await filterBar.evaluate(
          (el) => window.getComputedStyle(el.parentElement!).backgroundImage !== "none"
        );

        console.log(
          `[INFO] Filter bar fade gradient: ${gradientVisible ? "visible" : "not visible"}`
        );

        await context.close();
      });

      // 375px: Deep Dive panel opens full-screen
      test(`[375px] Deep Dive opens full-screen on mobile`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".story-card", { timeout: 5000 });

        // Click first story card to open Deep Dive
        const firstCard = page.locator(".story-card").first();
        await firstCard.click();

        // Wait for Deep Dive to appear
        const deepDive = page.locator(".deep-dive-panel");
        await deepDive.isVisible({ timeout: 3000 });

        const deepDiveBox = await deepDive.boundingBox();

        if (deepDiveBox) {
          // On mobile, should be full-screen (inset: 0)
          expect(deepDiveBox.width).toBe(375);
          expect(deepDiveBox.height).toBe(MOBILE_HEIGHT);
        }

        // Check close button is visible
        const closeBtn = page.locator(".deep-dive-close");
        const closeBtnVisible = await closeBtn.isVisible();

        expect(closeBtnVisible).toBe(true);

        await context.close();
      });

      // 375px: BiasLens SVGs fit within story cards
      test(`[375px] BiasLens fits within story card footer`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".story-card", { timeout: 5000 });

        // Check first BiasLens
        const firstBiasLens = page.locator('[class*="bias"]').first();
        const box = await firstBiasLens.boundingBox();

        if (box) {
          // BiasLens should be relatively compact on mobile
          if (box.width > 100) {
            // Rough estimate
            throw new Error(
              `[MEDIUM] BiasLens appears too wide on mobile: ${box.width}px`
            );
          }
        }

        await context.close();
      });

      // 375px: Footer fits and doesn't overflow
      test(`[375px] Footer fits without horizontal overflow`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        // Scroll to bottom
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        const footer = page.locator(".site-footer");
        const footerExists = await footer.isVisible();

        if (footerExists) {
          const footerBox = await footer.boundingBox();

          if (footerBox) {
            if (footerBox.width > 375) {
              throw new Error(
                `[HIGH] Footer exceeds 375px width: ${footerBox.width}px`
              );
            }
          }

          // Check footer items don't overflow
          const footerInner = page.locator(".site-footer__inner");
          const innerBox = await footerInner.boundingBox();

          if (innerBox && innerBox.width > 375 - 32) {
            throw new Error(
              `[HIGH] Footer inner content exceeds available width`
            );
          }
        }

        await context.close();
      });

      // Typography clamp() values check at 375px
      test(`[375px] Typography clamp() produces readable sizes`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        // Check hero text size at 375px
        const heroSize = await page.evaluate(() => {
          const hero = document.querySelector(".lead-story__headline");
          if (hero) {
            return parseFloat(window.getComputedStyle(hero).fontSize);
          }
          return 0;
        });

        // At 375px, --text-hero clamp(2rem, 1.5rem + 2vw, 4rem)
        // = clamp(32px, 24px + 7.5px, 64px) = 31.5px (clamped to min 32px)
        // Actually at 375px: 24 + (375 * 0.02) = 24 + 7.5 = 31.5 < 32, so min
        if (heroSize < 28 || heroSize > 36) {
          console.warn(
            `[INFO] Hero text size at 375px: ${heroSize}px (expected ~32px)`
          );
        }

        // Check it's readable (not too small)
        expect(heroSize).toBeGreaterThan(24);

        await context.close();
      });

      // Touch target sizes (44x44px minimum)
      test(`[375px] Touch targets are >= 44x44px`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        await page.waitForSelector(".story-card", { timeout: 5000 });

        // Check story card minimum height
        const storyCard = page.locator(".story-card").first();
        const cardBox = await storyCard.boundingBox();

        if (cardBox) {
          // Story card should have enough padding to be tappable
          const minHeight = 44; // Plus padding
          if (cardBox.height < minHeight - 10) {
            // Allow some flexibility
            console.warn(
              `[MEDIUM] Story card height less than expected: ${cardBox.height}px`
            );
          }
        }

        // Check nav buttons
        const navTabs = page.locator(".nav-bottom-tab");
        if ((await navTabs.count()) > 0) {
          const firstTab = navTabs.first();
          const tabBox = await firstTab.boundingBox();

          if (tabBox && (tabBox.height < 44 || tabBox.width < 44)) {
            throw new Error(
              `[CRITICAL] Nav tab below 44x44px: ${tabBox.width}x${tabBox.height}px`
            );
          }
        }

        await context.close();
      });

      // Page padding at 375px
      test(`[375px] Page padding doesn't squeeze content`, async ({
        browser,
      }) => {
        const context = await browser.newContext({
          viewport: { width: 375, height: MOBILE_HEIGHT },
        });
        const page = await context.newPage();

        try {
          await page.goto(urlConfig.url, { waitUntil: "networkidle" });
        } catch (e) {
          if (urlConfig.skipIfOffline) {
            test.skip();
          } else {
            throw e;
          }
        }

        // --space-7 at 375px = clamp(2rem, 1.5rem + 2vw, 4rem)
        // = clamp(32px, 24px + 7.5px, 64px) = 31.5px ~ 32px
        const padding = await page.evaluate(() => {
          const main = document.querySelector(".page-main");
          if (main) {
            const style = window.getComputedStyle(main);
            return {
              paddingLeft: parseFloat(style.paddingLeft),
              paddingRight: parseFloat(style.paddingRight),
              width: parseFloat(style.width),
            };
          }
          return { paddingLeft: 0, paddingRight: 0, width: 0 };
        });

        // Content width should be: 375 - padding*2
        const expectedWidth = 375 - padding.paddingLeft - padding.paddingRight;
        const tolerance = 2; // Allow 2px tolerance

        if (Math.abs(padding.width - expectedWidth) > tolerance) {
          console.warn(
            `[INFO] Page main width mismatch: ${padding.width}px vs ${expectedWidth}px`
          );
        }

        // Should have enough room for content
        expect(padding.width).toBeGreaterThan(300);

        await context.close();
      });
    });
  });
});

// Additional test for responsive breakpoints
test.describe("Responsive Breakpoint Validation", () => {
  const breakpoints = [
    { name: "375px (mobile)", width: 375 },
    { name: "390px (mobile)", width: 390 },
    { name: "414px (mobile)", width: 414 },
    { name: "768px (tablet)", width: 768 },
    { name: "1024px (desktop)", width: 1024 },
  ];

  breakpoints.forEach(({ name, width }) => {
    test(`[${name}] No horizontal scrollbar`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width, height: 800 },
      });
      const page = await context.newPage();

      try {
        await page.goto(LOCAL_URL, { waitUntil: "networkidle" });
      } catch (e) {
        test.skip();
      }

      await page.waitForTimeout(1000);

      const scrollWidth = await page.evaluate(
        () => document.documentElement.scrollWidth
      );
      const clientWidth = await page.evaluate(
        () => document.documentElement.clientWidth
      );

      expect(scrollWidth).toBeLessThanOrEqual(clientWidth);
      await context.close();
    });
  });
});
