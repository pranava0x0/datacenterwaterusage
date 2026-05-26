# DESIGN.md — Visual language

> Water as resource, not metaphor. The dashboard is about real data
> centers and real watersheds; the aesthetic should evoke the subject
> matter quietly, never decoratively.

---

## 1. Aesthetic principles

1. **Restrained, not playful.** Public-interest tracker, not a
   marketing site for water. No cartoon droplets, no falling-rain
   animations, no wave loops that compete with the data.
2. **Blue palette anchored to deep water.** Primary `#08519c` (deep
   blue) reads as authoritative and watery without going into pool /
   bathtub territory.
3. **Texture, not pattern.** A near-invisible droplet motif on the
   page background gives surface to the canvas; large explicit
   illustrations would distract.
4. **Status reads at a glance.** Color carries semantic meaning —
   green = enacted / blue = introduced / red = failed/vetoed. Never use
   palette colors for decoration that conflict with these signals.
5. **Plot-data ink dominates.** Backgrounds, decorations, and chrome
   sit at ≤10% opacity. Anything above that is showing real data.

---

## 2. Color tokens

Defined in `dashboard.py:COLORS`.

| Token | Hex | Used for |
|---|---|---|
| primary | `#08519c` | Headings, Introduced status pill, local-context card border, range-bar end |
| secondary | `#3182bd` | Mid-blue accents |
| tertiary | `#6baed6` | Light-blue accents |
| light | `#bdd7e7` | Range bar gradient start |
| bg | `#eff3ff` | Light card backgrounds, info-box fill |
| success | `#2e8b57` | Enacted pill, Delivered assessment |
| warning | `#d4a017` | Partial / Contested assessment |
| danger | `#c41e3a` | Failed / Vetoed pill, Shortfall assessment, permit-limit line |
| text | `#1a1a2e` | Body text |

Page surface uses `#f5f9fc` — a near-white with a barely-perceptible blue tint.

---

## 3. Background — the water texture

The Streamlit app container carries an inline SVG droplet pattern,
injected via `utils/device.py:_RESPONSIVE_CSS` and applied by
`inject_responsive_css()` at the top of every render:

- 120×120 px tile, four small teardrop ellipses per tile, all at
  ~5% opacity.
- `background-attachment: fixed` so scrolling doesn't shear the
  texture against content motion.
- Pattern color is `primary` (`#08519c`), low alpha — reads as water,
  not as pixels.

A faint wave decoration sits beneath the `h1` title — a short SVG
sine-wave underline at `secondary` (`#3182bd`) blue, low alpha. One
hint of motion, no animation.

---

## 4. Typography

- **System serif for h1** when long (browser default `serif` stack);
  system sans for h2/h3/body. No web fonts — keeps cold-start on
  stlite/github.io reasonable.
- Bill cards: bill_id **`1.05rem` bold**; status pill **`0.78rem`
  letter-spacing 0.02em**; summary inherits body size.
- `st.caption` is the right primitive for any attribution / sponsor /
  source-link line; never hand-roll a `<span style="font-size:0.9em">`.

---

## 5. Components

- **Bill card** (`_render_bill_card`) — `st.container(border=True)`;
  bill_id (bold) and status pill (colored rounded-rect, 999px radius)
  in a flex row; summary as a paragraph; sponsor + Source link as
  `st.caption`.
- **Claim card** (`_render_water_claim_card`) — same border treatment;
  verbatim quote in italic curly quotes; attribution + optional
  `Project: <id>` as `st.caption`; delivered-vs-promised uses the
  semantic Streamlit boxes (`st.success` / `st.warning` / `st.error`).
- **Local context card** (`.context-card`) — 4 px left border in
  `primary`; large number (`1.8rem` bold); comparison text; source
  note in muted gray.
- **Hero metrics** (`st.metric`) — 4-column on desktop, 2-column on
  mobile/tablet.
- **Lazy toggles** (`st.toggle`) — heavy panels (timeline, claims,
  source breakdown, heatmap, scorecard, per-query explainer, records
  table) load only on user opt-in.

---

## 6. Don'ts

- No animated rain, falling droplets, wave loops, or parallax.
- No turquoise / aqua / teal. Stay in the blue family of the existing
  palette.
- No drop shadows on cards — borders only.
- No background that competes with data tables or charts for visual
  weight.
- No emoji in headers (the body uses 💧 in `page_icon` only).
- No purely decorative color — every color in a card or pill should
  encode meaning.
