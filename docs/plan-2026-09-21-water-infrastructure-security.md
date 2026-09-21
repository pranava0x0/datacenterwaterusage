# Water Infrastructure Security research + graph follow-through

Date: 2026-09-21

## Assessment

The Explore work has two different results:

- **Text search panned out.** A realistic siting paragraph returns relevant cases,
  readings, claims, and sites, shows the matched terms, stays fully local, and
  links to the underlying record.
- **The full connection graph did not pan out as the primary interface.** With
  380+ nodes, the unfocused canvas is an overview, not an explanation. The
  default two-hop view can still expose dozens of records (80 in a live check),
  producing a hairball even though the underlying edges are sound.

Keep the graph, but make its evidence readable: default to one hop and render a
direct-connection list with edge labels. Do not add the security research to the
registry in this pass; that would enlarge the canvas before the security schema
has stable cross-reference semantics.

## Research method

Three bounded passes, followed by main-session source verification:

1. News/data changes since 2026-08-24: six named search angles, stop at eight
   verified additions/updates.
2. Water-security landscape: demonstrated threats, capabilities, suppliers,
   public institutions, and investment; primary government/lab/procurement
   sources preferred.
3. Federal program precedents: EPA/INL Water Security Test Bed, DOE CyTRICS,
   LLNL/ORNL capabilities, EPA/CISA/WaterISAC/WARN delivery, Project Glasswing,
   OpenAI Daybreak, and Texas Project Watershed 250.

Claims are tagged by evidence strength. Vendor case studies do not become proof
of broad deployment. Funding is labeled as appropriation, available program,
selected award, or local purchase; broad SRF/BIL water totals are not counted as
security spending.

## Product plan

### 1. Refresh current records

- Update signed California bills, Texas enforcement, and Meta/Newton County.
- Add distinct Nevada, Oregon, and Gilroy instruments.
- Add dated News entries pointing back to the affected records.
- Leave monitor baselines and page-chrome fingerprint changes out of curated
  data.

### 2. Add `water_security.json`

New append-only dataset, outside the registry for v1:

- `threats`: demonstrated cyber, insider, ransomware/IT-to-OT, and physical /
  contamination pathways.
- `capabilities`: concrete controls and delivery capabilities.
- `companies`: selected suppliers with verified capability and an explicit
  evidence limit; not a market-share ranking.
- `public_players`: agencies, laboratories, sector bodies, and state delivery
  networks.
- `investments`: amounts with funding status and anti-double-count notes.
- `precedents`: reusable operating models.
- `proposal`: Project Confluence — governance, roles, service loop, regional
  nodes, milestones, outcomes, and guardrails.

Every record carries at least one source URL. Tests enforce ids, required fields,
source URLs, enum membership, and unique ids.

### 3. Add a dedicated Security tab

One shared HTML builder feeds Streamlit and the static site. Section order:

1. What can go wrong.
2. What defense requires.
3. Who is in the field — public institutions and selected companies.
4. What is actually funded, with an honest “no national total” note.
5. Project Confluence: `Assess → Test → Exercise → Fix → Share`.
6. Phased 12/36/60-month outcomes and guardrails.

The tab is research, not a live threat feed and not procurement advice.

### 4. Improve Explore

- Default focus depth: one hop.
- Show direct connections as text with their relationship labels.
- Retain the two-hop option and canvas for overview.
- Keep security records out of graph v1; revisit only after cross-reference
  fields exist and direct-list behavior is validated.

## Verification

- Curated-data schema tests.
- Static build tests.
- Full `python3 -m pytest -q`.
- Rebuild all generated artifacts twice and require no diff.
- Browser check: Security tab content, source links, mobile containment, Explore
  one-hop default, direct connection list, and no console errors.
- Spot-check every added URL; 404 is a blocker, 403 is inconclusive only where
  the project already records bot blocking.

