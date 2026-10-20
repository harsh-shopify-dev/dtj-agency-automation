# Codebase map and how to build

## Where things are

- Site repo: `D:\CODE CONTAINERR\WEB DEV\DTJ` (GitHub `harsh-shopify-dev/dtj-website`). Next.js 16.3 (Turbopack, app router),
  React 19, Tailwind v4.3, GSAP + Lenis. Read its `HANDOFF.md` first; it is the running log.
- Work branch: `feature/landing-v2` (as of 10 Oct 2026, all variant work uncommitted). Never commit to `main`, never force-push,
  and commit or push only when Harsh asks. `.claude/` and the three raw logo files in the root stay untracked.
- Next.js here has breaking changes: read `node_modules/next/dist/docs/` before using an unfamiliar API.

| Path | What |
|---|---|
| `app/page.tsx` | `/` original page (control). Don't change it unless Harsh asks. |
| `app/v2/page.tsx` | `/v2` (the full page's sections + audit fixes, short copy via the `brief` props) |
| `app/<slug>/page.tsx` | one simple pain page each (`ads-no-orders`, `sales-stuck`, `website-no-sales`) |
| `app/audit/page.tsx` | `/audit`: founder-led page with the 5-step form as the hero (`AuditLanding`, copy in `components/simple/audit-content.ts`) |
| `app/landing-fixes.css` | `.lp-fixes` contrast/size fixes for all variants (imported by each variant route) |
| `components/simple/content.ts` | **all copy for the pain pages** (`PainPage` entries) |
| `components/simple/*.tsx` | `SimpleLanding`, `SimpleHero`, `PainSections` (Symptoms, Fixes), `Proof` (hero cards, results, logos, case stories), `SimpleReviews`, `SimpleForm`, `FounderBand`, `StickyCta`, `StepForm`, `AuditSections` (TodayVsAfter, AuditContents), `AuditLanding`, `styles.ts` |
| `components/v2/*` | `FormLink`, `HowItWorks` (`STEPS`), `Faq`, `SkipLink`, `HeaderCtaLabel` |
| single sources | `RealResults.tsx` `ROWS`, `CaseStudies.tsx` `caseStudies`, `ReviewsMasonry.tsx` `reviews`/`ReviewCard`, `ClientShowcase.tsx` `CLIENTS`, `hero/data.ts`, `TrustStrip.tsx` |
| `public/submit.php` | form handler (email, Sheet, WhatsApp alert). Each lead carries `page_url`, so variants are told apart in the Sheet. |

## Add a pain page

1. Add an entry to `components/simple/content.ts` (copy rules: `audience-and-voice.md`; claims: `claims-and-proof.md`):

```ts
export const NEW_PAIN: PainPage = {
  slug: "agency-unclear",
  title: "Paying an agency but no clarity? | Digital Tushar Joshi",
  description: "One sentence for search/social previews.",
  headline: { plain: "Paying an agency every month, but", accent: "no idea what's working?" },  // ≤ 9 words
  sub: "One plain promise restating a DTJ service.",                                   // ≤ 14 words
  heroProof: "meta-report",          // "meta-report" | "page-screens" | "royal-dosa"
  symptoms: ["four things the founder recognises", "...", "...", "..."],             // ≤ 7 words each
  fixes: [{ problem: "general cause", fix: "restated DTJ service" }, { problem, fix }, { problem, fix }],  // ≤ 7 words a side
  faq: [FREE, NEXT, NOTHING /* + one page-specific, confirmed answers only; 4 in total */],
};
```

2. Create `app/<slug>/page.tsx` (copy an existing one; it imports `SimpleLanding`, the entry, `../landing-fixes.css`, and sets
   `title`, `description`, `robots: { index: false, follow: false }`).
3. Results, case studies, reels and reviews appear on every page automatically (all of them). Run the gates
   (`qa-and-handoff.md`). New block types belong in `components/simple/` using `styles.ts`.

## Run it

- From a dtj-agency-automation session: `preview_start` with name `dtj-landing` (in `.claude/launch.json`; it `Set-Location`s
  into the DTJ folder and runs `npm run dev -- -p 3100`, because npm breaks on the spaces in the path). Pages at
  `http://localhost:3100/<slug>`.
- From a terminal: `cd "D:\CODE CONTAINERR\WEB DEV\DTJ"` then `npm run dev -- -p 3100`.
- Hostinger build: stop the dev server first (both use `.next`), then `npm run build:hostinger` → `deploy/landing-page.zip`
  (base path `/free-growth-audit`; every route exports, e.g. `/free-growth-audit/sales-stuck/`). Uploading is Tier 2: ask Harsh.

## Gotchas (all hit for real)

- **`/` shows "not found" although `app/page.tsx` exists:** stale dev cache from the Hostinger build. Stop the server, rename
  `.next/dev` to `.next/dev.stale-<date>`, restart.
- **"Cannot access X on the server":** a server component can't read plain data (`ROWS`, `reviews`, `caseStudies`) exported
  from a `"use client"` module. Put the reading component in a `"use client"` file (as `Proof.tsx`, `SimpleReviews.tsx` do).
- **Class strings:** an optional prop must not reorder the default class string, or `/`'s HTML changes; append conditionally.
- **Tailwind v4 variants used:** `pointer-coarse:`, `max-lg:`, `min-[380px]:`, `motion-safe:`. Arbitrary classes like
  `text-[10px]` are targeted by `.lp-fixes` CSS (phones get 12px).
- **Swipe rows widen the page:** a horizontal `overflow-x-auto` row must be `relative`, or its cards' absolutely positioned
  `sr-only` text (e.g. "Google review") anchors to the page and off-screen cards add thousands of px of sideways scroll.
- **Screenshots:** Chromium can't capture full pages taller than 16,384 px (blank below). Phone pages are ~7k px today.
- **Local production build from Git Bash:** `export MSYS_NO_PATHCONV=1 MSYS2_ENV_CONV_EXCL='*'` first, or the base path env var
  becomes a Windows path and `next build` fails. Stop the dev server first. To measure speed like a real host, serve `out/`
  under a `free-growth-audit/` folder with gzip (a plain `python -m http.server` doesn't compress and doubles the numbers).
- **Speed (12 Oct 2026, slow 4G phone, gzip):** `/audit` LCP ~2.0 s, pain pages 2.2–2.9 s. Keep it there: no video embeds,
  sliders or animation libraries on the variants; heavy media below the fold loads lazily (`lazyPosters`).
- **Git Bash:** URLs/paths starting with `/` in arguments get rewritten; `export MSYS_NO_PATHCONV=1` before curl. `python -I`
  ignores `PYTHONIOENCODING`; call `sys.stdout.reconfigure(encoding="utf-8")` before printing ₹.
- **Built-in browser:** screenshots time out when the pane is hidden; retry once, or use `get_page_text`/`find`. Figma's design
  canvas can't be zoomed by keys there; use the prototype URL (see `page-anatomy.md`).
