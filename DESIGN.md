# DESIGN.md — Visual language

> Water as resource, not metaphor. The dashboard tracks real data
> centers and real watersheds; the aesthetic evokes the subject
> matter quietly, never decoratively.

---

## 1. Aesthetic principles

1. **Restrained, not playful.** Public-interest tracker, not a
   marketing site for water. No cartoon droplets, no falling-rain
   animations, no wave loops that compete with the data.
2. **Blue palette anchored to deep water.** Primary `#08519c` (deep
   blue) reads as authoritative and watery without going into pool /
   bathtub territory.
3. **Infrastructure texture, not illustration.** Both surfaces carry the
   same near-invisible water tile plus a handful of pipe-fitting marks
   (section headers, the active tab, the footer strip) — all ≤12%
   opacity, all texture rather than art. The single exception is the
   header water-loop schematic: it is a labeled diagram carrying
   information, so it is drawn at full palette strength. See §3.
4. **Status reads at a glance.** Color carries semantic meaning —
   green = enacted / working, blue = introduced, red = failed / vetoed /
   blocked, amber = partial / pending, purple = coming soon.
   Never use palette colors decoratively in ways that conflict with
   these signals.
5. **Plot-data ink dominates.** Background and ornament layers — the
   page texture, the footer pipe run — sit at ≤12% opacity (the texture
   itself at 6–8%). Structural chrome (section-header borders and their
   fittings, the active-tab pipe, rules) is full-strength but stays
   monochrome blue and never borrows a status color. Anything else drawn
   above texture strength is showing real data.

---

## 2. Color tokens

Defined in `dashboard.py:COLORS`.

| Token | Hex | Used for |
|---|---|---|
| primary | `#08519c` | Headings, Introduced pill, section accent borders, pipe motif |
| secondary | `#3182bd` | Mid-blue accents, h1 wave underline, `.solution-cat-header` left border |
| tertiary | `#6baed6` | Light-blue accents, hr gradient end |
| light | `#bdd7e7` | Range bar gradient start, outline chip border |
| bg | `#eff3ff` | Light card backgrounds, info-box fill, principle chips |
| success | `#2e8b57` | Enacted pill, Working source badge, Delivered assessment |
| warning | `#d4a017` (`#b45309` text) | Partial / Pending / Contested |
| danger | `#c41e3a` | Failed / Vetoed / Blocked, Shortfall assessment |
| purple | `#7c3aed` | Coming-soon source badge, upcoming-unlock timeline |
| text | `#1a1a2e` | Body text |

Page surface: `#eaf4fb`, under the three-layer water ground described in
§3 (`#f2f9fd → #e6f2fa → #d8ebf6`). Cards sit on `#fff` above it.

---

## 3. Water & infrastructure surface

Everything here exists on **both surfaces**. The Streamlit app gets it
from `assets/components.css` (loaded at import as
`utils/device.py:_RESPONSIVE_CSS`, injected by `inject_responsive_css()`);
the static site inlines that same file as `build_site.COMPONENT_CSS` and
adds its page-level rules in `build_site.CSS`. Nothing here loads from a
network — every asset is an inline `data:` URI or inline SVG.

**Page background** — three layers, back to front, `background-attachment:
fixed` on all three so scrolling doesn't shear them:

1. a soft radial white highlight top-center — light on a water surface;
2. a top-to-bottom depth wash, `#f2f9fd → #e6f2fa → #d8ebf6`;
3. a 240×120 tile of three staggered ripple lines + scattered bubbles,
   `#08519c`/`#3182bd` at 6–8% opacity. The ripple period (40px) divides
   both tile dimensions, so it tiles seamlessly in both axes.

The tile replaced an earlier pipe-and-droplet schematic in July 2026:
open water reads better as a ground than plumbing does, and the plumbing
motif now lives where it means something (fittings, schematic).
`@media print` drops the whole background — it prints as grey mush.

**h1 wave underline** — 80px double-amplitude SVG sinusoid at `#3182bd`,
opacity 0.65, `stroke-width:1.5`, repeating on `x`, anchored `left bottom`.

**Horizontal rules** — `st.divider()` maps to `.stApp hr`; the static page
styles bare `hr`. Pipe-flow gradient: `#08519c → #3182bd → #6baed6 →
transparent`, `height:2px`, `border-radius:1px`, no `border`.

**Pipe fittings** — a 10px `#3182bd` dot capping the top of the left
border on `h3.solution-cat-header` / `h4.solution-cat-header` (§9), and
the active tab's marker: a 2px round-capped `#08519c` bar with a fitting
dot at each end (`::after` + one `::before` carrying two radial
gradients). Scoped to `h3`/`h4` because the static Solutions accordion
hangs the same class on a `<summary>` span with the border removed.

**Footer pipe run** — a 960×26 inline SVG above the footer note: pipe,
five fittings, a gate valve, three rack silhouettes. Ornament, so
`opacity:.12`, `aria-hidden`, no labels, and `display:none` in print.

### Header water-loop schematic

`dashboard._build_water_loop_svg()` — pure, returns a self-contained
`<div class="schematic">` + inline SVG. `build_site.build_html()` inlines
the same string under the h1; `dashboard.main()` renders it under the
title. One definition, two surfaces, test-enforced.

It is the one piece of art on either surface that is data-ink, because it
explains the project's own architecture: **river/wellfield intake →
treatment plant → data center hall (three slotted racks) → closed chiller
loop → cooling tower → blowdown → sewer → wastewater plant → treated
effluent back to the river.** Two annotations carry the two facts the
whole tracker rests on:

- *evaporation is the consumptive loss — this water leaves the basin, not
  the sewer* (at the cooling-tower drift), and
- *the sewer leg is metered on the receiving plant's NPDES permit — that
  is where the data shows up* (under the sewer→WWTP leg), which is why
  the pipeline's primary source is EPA ECHO DMR data from receiving WWTPs
  rather than anything a data center files itself.

Conventions: a 960×124 viewBox so one unit ≈ one pixel at content width;
station labels 11 units (≈0.7rem) in `#4b5563` under each element — the
river's sits above it, because the return leg runs underneath;
annotations 10 units in `#08519c`. The pipe run is an **open** path
(intake → outfall → back up into the river): the river closes the loop,
not a pipe. Below ~900px of drawing width the labels stop being legible,
so `.schematic` scrolls horizontally rather than shrinking the type
(print drops that minimum so the diagram fits the sheet). Everything but
the animation uses presentation attributes, so a surface that strips
`<style>` still gets a correct diagram — it just stops moving.

**The one sanctioned animation.** Pale dashes (`stroke-opacity` 0.35)
drift along the pipe: `stroke-dasharray:6 22`, `stroke-dashoffset` to
`-1680` over 24s linear, infinite. The offset is a whole number of dash
periods so the loop has no visible jump. Off entirely under
`@media (prefers-reduced-motion: reduce)`, which leaves the dashes as
static direction ticks. Nothing else on either surface animates (§12).

---

## 4. Typography

- **System sans-serif for all text.** No web fonts — cold-start on
  GitHub Pages must stay under 50 KB of blocking resources.
- `st.subheader()` = h2 — used **once per tab** as the tab title.
  Never use it for section headers within a tab.
- `h3.solution-cat-header` — section / group headers within a tab
  (pipe-left-border accent). See §9.
- Sub-group level dividers (e.g., "Federal" / "Virginia" within the
  source table) — small-caps style, `#08519c`, 0.83rem. Not a
  `.solution-cat-header`; these are inside an existing section.
- `st.caption()` — attribution, source links, dataset-last-updated
  footer. Never hand-roll a `<span style="font-size:small">`.

---

## 5. Tab anatomy — standard structure

Every content tab follows this pattern (in order):

```
st.subheader("Tab Title")              # exactly one per tab, at the top
st.markdown("One-liner description.")  # always present
[summary panel]                        # always present — see §6
[filter controls, if filterable]       # st.multiselect with explicit key=
[count line, if filterable]            # "**N of M items**"
st.divider()
[content: cards / sections]
st.caption(f"Dataset last updated {last_updated}.")  # bottom of every tab
```

Tabs without user-facing filters (Sources) omit the filter and count
lines, but keep all other elements including the summary panel and caption.

---

## 6. Summary panels — "what's the overall picture?"

Every content tab leads with a panel that answers the overview question
before the user scrolls into the card list. Panel shape varies by data type:

| Tab | Panel |
|---|---|
| Legislation | Principles panel (cross-bill taxonomy counts) + theme grid (6 themes) |
| CWA Cases | Datacenter insights callout + application-theories table |
| News | 3-metric row: Headlines / Topics / Most recent date |
| Solutions | 6-metric row (Deployed/Pilot/Proposed × Mandate/Utility/Industry) + key-patterns callout |
| Sources | 4-metric scorecard: Accessible / Blocked / Unlocking / Queue |

These panels are rendered by dedicated builder functions so the same
logic runs in both the Streamlit app and `build_site.py`.

---

## 7. Card system

Three card variants are used across tabs — they look nearly identical
but are rendered differently:

| Card class | Border | Shadow | Tab |
|---|---|---|---|
| `.bill-card` | `1px solid #cbd5e1` | `0 1px 2px rgba(15,23,42,.04)` | Legislation, CWA Cases |
| `.solution-card` | `1px solid #d6e4f0` | `0 1px 2px rgba(15,23,42,.04)` | Solutions |
| news card (inline styled) | `1px solid #d6e4f0` | none | News |

All three: `border-radius:0.5rem`, `padding:~1rem`, `background:#fff`.

**Inside every card (consistent across all three):**
- **Title** — bold, 1rem–1.05rem, `color:#1a1a2e`
- **Status / type badges** — see §8
- **Body** — 0.9rem, `color:#1a1a2e`, `line-height:1.5`
- **Meta line** — 0.82–0.85rem, `color:#4b5563`; source link in `#08519c`
- **Stat / example callout** — left-border block (`.solution-example`,
  `.cwa-pathway`, `.cwa-takeaway`). See §10 for colors.
- **Cross-ref arrow** — `→ link text`, `color:#08519c`, `font-size:.82rem`
- **Expand toggle** — `▸ Details — ...` in `#08519c`, via `<details>` native

---

## 8. Badge / pill system

Two distinct shapes encode two distinct things:

| Shape | Used for | Key CSS |
|---|---|---|
| **Filled pill** | Primary status (Enacted, Blocked, Deployed…) | solid `background`, `color:#fff`, `border-radius:999px`, `.78rem`, weight 700 |
| **Outline chip** | Type tags, principle chips, scope labels | light `background`, dark `color`, `border:1px solid mid`, `border-radius:999px`, `.75rem`, weight 600 |
| **Tinted pill** | Source-row status in Sources tab | light `background-tint` of the status color + matching `border`, dark `color`, `border-radius:999px`, `.75rem` |

**Never** use Markdown backtick code marks (`` `label` ``) for status.
Backticks render as `<code>` elements and look like inline code.

Status color semantics (applies to all pill variants):

| Status | Text color | Background | Border |
|---|---|---|---|
| Working / Enacted | `#2e8b57` | `#f0fdf4` | `#86efac` |
| Partial / Pending | `#b45309` | `#fffbeb` | `#fde68a` |
| Blocked / Failed | `#c41e3a` | `#fff1f2` | `#fecaca` |
| Coming soon | `#7c3aed` | `#f5f3ff` | `#ddd6fe` |
| Not built / Gap | `#6b7280` | `#f9fafb` | `#e5e7eb` |

---

## 9. Section headings within tabs

When a tab has sub-groups (e.g., "Policy & Regulatory / Technology &
Operational" in Solutions; "Federal / Virginia / Ohio" in Sources),
each group header uses `.solution-cat-header`:

```html
<h3 class="solution-cat-header">Group Name</h3>
```

CSS in `assets/components.css`:
```css
.solution-cat-header {
    font-size: 1rem;
    font-weight: 700;
    color: #08519c;
    border-left: 4px solid #3182bd;
    padding-left: 0.7rem;
    margin: 1.2rem 0 0.3rem;
}
```

Emit via `st.markdown('<h3 class="solution-cat-header">…</h3>', unsafe_allow_html=True)`.

Do **not** use `#### Heading` markdown — that renders as h4, which is smaller
and carries no pipe accent. Do **not** use `st.subheader` for section headers;
that's reserved for the one tab-level title.

---

## 10. Barrier / callout cards

Semantic callouts (barriers, pathway explanations, key-patterns) always use
the left-border HTML pattern — **never** `st.error / st.warning / st.info`
except for genuine user-facing error states (empty dataset, network failure):

```html
<div style="border-left:3px solid {color};background:{bg};
            padding:.65rem .9rem;border-radius:0 .4rem .4rem 0;">
  <strong style="color:#1a1a2e;">{title}</strong>
  <p style="margin:.35rem 0;font-size:.88rem;color:#1a1a2e;">{body}</p>
</div>
```

Semantic colors (matches §8 status palette):

| Kind | Border | Background |
|---|---|---|
| Error / structural barrier | `#c41e3a` | `#fff1f2` |
| Warning / legal / policy concern | `#b45309` | `#fffbeb` |
| Info / pending CWA pathway | `#3182bd` | `#eff3ff` |
| Success / enacted / takeaway | `#2e8b57` | `#f0fdf4` |

---

## 11. Timeline rows

Chronological event lists use `.timeline-event` CSS classes (defined in
`assets/components.css`):

```html
<div class="timeline-event">
  <div class="timeline-date" style="color:{color};">{date}</div>
  <div class="timeline-body">
    <strong>{title}</strong>
    <div class="timeline-detail">{desc}</div>
  </div>
</div>
```

Date column color: `#2e8b57` for enacted/live events, `#7c3aed` for coming-soon.

**Never** use `{emoji} **bold** · *italic*\n{desc}` inline markdown for
timeline items — the CSS class approach renders consistently and is
easier to restyle without touching every call site.

---

## 12. Don'ts

- No animated rain, falling droplets, wave loops, or parallax.
- **One animation is sanctioned: the header schematic's flow line
  (§3). Nothing else moves.** It is CSS `@keyframes`, so the page must
  contain exactly one `@keyframes` block — a build test asserts that.
  (The Explore graph's force layout settles once on load and honors
  `prefers-reduced-motion`; a layout computation is not decoration.)
- No turquoise / aqua / teal. Stay in the blue family of the palette.
- No backtick code marks (`` `status` ``) for status badges — use
  styled HTML spans with the tinted-pill pattern.
- No `st.error / st.warning / st.info` as design elements. Those are
  for genuine user-facing error states only. Use the left-border HTML
  callout pattern for semantic annotations.
- No `#### heading` markdown for section headers within a tab. Use
  `h3.solution-cat-header` (pipe accent, `#08519c`).
- No `st.subheader` for sub-group headers within a tab — one per tab,
  for the tab title only.
- No emoji in headers.
- No purely decorative color — every color in a card or pill encodes
  meaning.
- No web fonts — system sans-serif only.
- No drop shadows heavier than `0 1px 2px rgba(15,23,42,.04)`.
