# Product page factory skills: the brief behind them (10 Oct 2026)

Two project skills live in `.claude/skills/` (in git, so both Claude accounts and every machine get the same version):
- `dtj-pdp-factory`: the end-to-end runbook (client setup, facts, wireframe plan, slot-by-slot design, build, review, approval,
  write, verify), with references for the wireframe, design method, colour and vibe, motion, intake, commands, errors, new blocks.
- `dtj-pdp-design-review`: the gate (palette vs vibe, repetition, first phone screen, CTAs, 100-point CRO rubric, blocking
  findings) with deterministic scripts: `palette_report.py`, `template_audit.py`, `page_audit.js`.

## Harsh's request, refined (the requirement these skills implement)
1. **One layout for every product page:** the ThrillX "Ecom Product Based Landing Page" wireframe (Figma file "Public Landing
   Page - ThrillX", frames `2460-4368` desktop and `2460-5367` mobile), slots W00-W16 in a fixed order. The model chooses which
   slots to fill from the facts; it never reorders or invents slots. Omissions are reported with the content that unlocks them.
2. **Analyse each section fully before designing it** (purpose, material, the block's real settings, words, visual and motion
   treatment, mobile form, CTA, self-check), with a claim ledger so nothing repeats.
3. **Fit the product's vibe:** colour, motion and type follow what the product promises (an energy mint must feel energetic; a
   kurta must not have marquees). Measured, not guessed (`palette_report.py` against `vibe_profiles.json`).
4. **Review like a CRO lead after every build:** full-page screenshots, palette analysis, problem-solution-proof story,
   repetition, CTAs, objections, mobile; a score, blocking findings, fixes mapped to the step that owns them; at most 3 rounds.
5. **Same result on any account or model:** decisions are tables and thresholds in the skill files; checks are scripts and lint
   rules; outputs use fixed templates; evals keep the behaviour stable.

Added beyond the original request (gaps the first Go Mints page exposed):
- Never invent proof, not even in demo mode; ask for content at intake (`facts-intake-checklist.md`), not at the end.
- Store hygiene before design: placeholder titles, sold-out products, unassigned templates.
- Missing blocks get BUILT (Harsh's decision, 10 Oct): G1 CTA / banner, G2 icon row, G3 FAQ with picture, G4 accordion in split
  story, G9 the wireframe as the builder's recipe; and V1, the vibe in `direction.py`.
- An errors playbook from everything that went wrong on 9-10 Oct (installs, catcher, Theme Access, CLI, Cloudflare, Figma).
- Two tools so no person has to add blocks in an editor: `install-catcher/tools/client_registry.py` and `licence_call.py`.
- Honest limit: the live-theme write has no approved tool (`--allow-live` is denied in `.claude/settings.json`); Harsh decides.
