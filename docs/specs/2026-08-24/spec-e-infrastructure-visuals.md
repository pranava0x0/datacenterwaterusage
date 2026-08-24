# Spec E — Water-infrastructure visual language on the static site

## Purpose

The Streamlit app carries the pipe-and-droplet texture, wave underline, and pipe-flow dividers; `pages/index.html` — the deployed surface — has none of them, and neither surface shows how water actually moves through a data center. Bring the infrastructure language to the static site and add the one piece of art that earns its ink: a labeled water-loop schematic. More water, servers, pipes, and cooling equipment, delivered as information and texture — DESIGN.md's "infrastructure texture, not illustration" rule stays in force.

## Changes (all in `build_site.py` CSS/HTML; DESIGN.md updated to match)

1. **Port the background texture.** The 200×200 pipe-and-droplet SVG tile (from `assets/components.css`) as an inline `data:` URI on `body`, ≤7% opacity, `background-attachment: fixed`. Remove DESIGN.md §3's "does not appear in the static site" caveat.
2. **Header water-loop schematic** (the centerpiece). Inline SVG under the h1, full content width, ~120px tall, drawn from the palette blues on the page surface. Left to right: **river/wellfield intake → treatment plant → data center hall (three server racks drawn as slotted rectangles) → CRAH/chiller loop (closed loop arrows) → cooling tower (hyperboloid silhouette with evaporation drift rising) → blowdown line → sewer → wastewater treatment plant → back to the river**. Labels in 0.7rem muted text under each element; two annotations carry the tracker's two core facts: evaporation is the consumptive loss, and the sewer path is why WWTP permits are where the data shows up. This is a diagram, not a decoration — it explains the pipeline's own architecture (why EPA ECHO DMR data from receiving WWTPs is the primary source).
3. **h1 wave underline + pipe-flow `hr` gradient** ported from the app styles (same specs as DESIGN.md §3).
4. **Section-header pipe fittings.** `.solution-cat-header`'s left border gains a small circular fitting dot at the top of the border (pure CSS `::before`), echoing the pipe-joint motif.
5. **Tab-strip cooling loop.** The active tab's underline gets a subtle pipe treatment: 2px, rounded caps, a small fitting dot at each end (CSS only).
6. **Footer motif.** A thin one-line SVG strip above the footer: pipe run with fittings, a valve, and three server-rack silhouettes, stroke `#08519c` at ~12% opacity.
7. **One sanctioned animation.** The schematic's flow path may animate `stroke-dashoffset` (~24s linear, one direction, opacity of the moving dashes ≤0.35), fully disabled under `prefers-reduced-motion: reduce`. Everything else stays static. DESIGN.md §12 gains: "One animation is sanctioned: the header schematic's flow line. Nothing else moves."

## Constraints

- All SVG inline or `data:` URIs — no new network assets, no SRI surface change, no fonts.
- Page-weight budget: everything in this spec adds ≤25 KB to `pages/index.html`.
- Dark-mode: the page is single-theme (light); keep it that way — no half-theme.
- Colors from the existing palette only; texture/ornament ≤12% opacity; the schematic uses full-strength palette strokes because it is data-ink.
- Print: schematic prints fine; texture suppressed via `@media print`.

## Streamlit surface

The schematic builder is a pure function returning SVG (shared), embedded in the app's hero too. Texture already exists there; no other app changes.

## DESIGN.md updates (living doc)

- §3 rewritten: texture now on both surfaces; schematic documented with its two annotations; sanctioned-animation rule.
- §12 "Don'ts" keeps: no rain, no cartoon droplets, no teal, no parallax. Adds the one-animation rule.

## Tests

- `tests/test_build_site.py`: schematic SVG present with its label strings ("evaporation", "cooling tower", the WWTP annotation); texture data-URI present on body CSS; page-size guard (existing or new: total `index.html` under a stated byte ceiling with headroom); `prefers-reduced-motion` block present if the animation is present.

## Out of scope → backlog

- Per-tab icon set (rack/pipe/droplet/tower next to tab labels) — worth doing only if it survives a design pass against §12's "no emoji in headers" spirit.
- Animated per-site water-flow visualizations on the Data tab.
