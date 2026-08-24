# Spec A — Federal water-statute completion + anchoring historical cases

## Purpose

The toolkit's federal layer stops at CWA, SDWA, TSCA, RCRA, RHA, ESA. A data center's water problem can just as easily run through a Corps storage contract, a NEPA supply analysis, a basin-commission docket, or a CERCLA plume. Add the missing federal families, each with (1) readings that state what the law historically covered and how it could reach a data-center fact pattern (`dc_applicability` — the same "guesses at applications" register the existing 39 readings use), and (2) at least one verified historical case per family in `cwa_investigations.json`, because a family with no case is a reading list, not a tool (the existing test suite enforces the pairing).

## Candidate families (research agent verifies; drop any that can't be anchored to a real case + plausible DC application)

| Code | Statute | Kind | Why a data center meets it | Historical anchor candidates (verify, don't confirm) |
|---|---|---|---|---|
| NEPA | National Environmental Policy Act, 42 U.S.C. §4321+ | federal-statute | §404/§408/FERC/federal-loan actions on DC projects trigger review; water-supply adequacy in an EIS is a recognized battleground | Hughes River Watershed Conservancy v. Glickman (4th Cir. 1996); a modern DC or transmission NEPA water fight if one is verifiable |
| CERCLA | Superfund, 42 U.S.C. §9601+ | federal-statute | Siting on/near plumes; groundwater pumping that migrates a plume; §107 liability for cooling-chemical releases | CTS Corp. v. Waldburger (2014); United States v. Bestfoods (1998) as owner/operator doctrine |
| WSA | Water Supply Act of 1958, 43 U.S.C. §390b | federal-statute | Municipal storage in Corps reservoirs is how growing loads get supply; reallocation fights are the closest analog to metro DC demand growth | The Lake Lanier/ACF litigation (Southeastern Fed. Power Customers v. Geren, D.C. Cir.; In re MDL-1824 Tri-State Water Rights (11th Cir. 2011)) |
| WRDA | Water Resources Development Acts + 33 U.S.C. §408 | federal-statute | Alterations to federal projects (intakes, outfalls, levee crossings) need §408 permission; WRDA carries reallocation and supply provisions | A verified §408 dispute; if none is strong, fold §408 into WSA family and drop WRDA |
| BASIN | Ratified basin compacts & commissions (Great Lakes Compact; DRBC; SRBC) | interstate | The Compact bans most out-of-basin diversion (Foxconn's Racine diversion — same Mount Pleasant site now hosting Microsoft); DRBC/SRBC approve large withdrawals directly, dockets are public | Racine/Foxconn diversion challenge (2018–21); a verified DRBC or SRBC large-withdrawal docket or enforcement |
| WSR | Wild & Scenic Rivers Act §7, 16 U.S.C. §1278 | federal-statute | Bars federally assisted water projects that harm designated reaches; VA/OR/WA DC corridors touch designated rivers | A verified §7 project denial/conditioning case |
| FPA | Federal Power Act (FERC hydropower licensing) | federal-statute | DCs co-locating at dams; license articles govern reservoir levels and flows; crypto-at-dams precedent | A verified license-amendment or flow-regime case |
| RECL | Reclamation law (1902 Act + Warren Act contracts) | federal-statute | Western DCs buying ag water delivered through federal projects need contract cover | A verified Reclamation contract/transfer dispute |
| EPCRA | Emergency Planning & Community Right-to-Know Act | federal-statute | Cooling-water treatment chemicals + diesel above thresholds trigger Tier II reporting — a transparency hook activists already use | A verified EPCRA citizen-suit or enforcement (Steel Co. v. Citizens for a Better Environment (1998) is the standing landmark) |
| OPA | Oil Pollution Act §311 overlay / FRP rules | federal-statute | Backup-generator diesel farms near navigable waters can trigger SPCC/FRP; distinct from the CWA §311 reading | A verified FRP/SPCC enforcement at a non-oil industrial facility; drop if it duplicates cwa-311-spills without adding a hook |
| FWCA | Fish & Wildlife Coordination Act | federal-statute | Rides every §404/§10 permit; historically the lever that forces mitigation | Likely folded as a reading under NEPA or dropped — standalone cases are thin; agent decides with evidence |

Target: ≥8 new families that survive verification, ~12–18 new readings, ~12–20 new historical cases. Prefer depth (a strong case, a precise reading) over count.

## Data changes

1. `data/reference/water_authorities.json`
   - `statutes` dict: one entry per surviving family — `name`, `full_name` (act name + U.S.C. cite), `agencies`, `url` (law.cornell.edu or agency page; never Justia), `kind`.
   - `readings`: per family, 1–3 entries with `reading_id` (kebab, family-prefixed), `statute`, `section`, `name`, `agency`, `what_it_covers` (historical, past-tense, cite-anchored), `dc_applicability` (the forward-looking guess: how this reaches a data-center fact pattern — concrete, one scenario per sentence), `example_case_ids`.
2. `data/reference/cwa_investigations.json`
   - New cases, mostly `category: precedent` (doctrine landmarks) or `industrial` (enforcement analogs). Every case: `case_id` (Name-v-Name-YYYY), `case_type` from the existing 11-value taxonomy, `cwa_applied: not-applied` where the action ran under another statute (the statute pills derive from `authorities`), `authorities` → new reading ids, `outcome_type` list from the existing 12-value taxonomy, `violation_summary`, `outcome`, `takeaway` (what it means for a data center, one or two sentences), `sources` (≥1 verified URL each), `year`, `display_section`, `cwa_instrument`.
   - Where a new reading genuinely reaches an existing tracked site (e.g., BASIN → Mount Pleasant WI; WSA → any ACF-basin Georgia site; CERCLA → a site on a plume), add `site.applicable_readings` mappings with per-site `how` text — same shape the 19 sites already use.
3. `refdata/taxonomies.py`: `WATER_STATUTE_ORDER` (new families after RHA, before EQAP, in rough hierarchy: NEPA, CERCLA, WSA, WRDA, WSR, FPA, RECL, EPCRA, OPA, then BASIN next to EQAP) and `WATER_STATUTE_COLORS` (distinct hues; stay out of turquoise/teal per DESIGN.md).

## Render changes

None structural — the Water Cases Part 1 accordion, statute pills, jump-nav, and filters are all data-driven from the statutes dict and readings. Verify the accordion doesn't become unusable at ~28 families; if the jump-nav row wraps past 3 lines, group pills by kind (federal statute / interstate / state doctrine / common law) with small-caps kind headers — a render-only change in `_build_authorities_html`.

## Tests

- Existing schema tests pick up most of it (family kind declared, order/colors agree, readings resolve, example cases resolve).
- Add: every `kind: federal-statute` family has ≥1 reading and ≥1 case reachable via `example_case_ids` (mirror of the doctrine-family test).
- Update any hardcoded counts (llms.txt coverage, accordion counts) the suite asserts.

## Research-agent brief (Sonnet)

Input: the candidate table above + existing reading/case id lists (to avoid collisions/duplicates). For each family: verify the statute cite, find 1–2 anchoring cases with two independent sources each (court opinions via WebSearch — never construct Justia/CourtListener URLs), and write the reading text + dc_applicability in the corpus register. Explicitly flag: families that don't survive (say why), cases that fit better in an existing family, and anything that doesn't fit the schema (misfits are design input, not failures). Output: one JSON file with `statutes`, `readings`, `cases`, `site_mappings`, `dropped` keys, to the scratchpad path given in the prompt.

## Out of scope → backlog

- International/treaty layer (Boundary Waters Treaty, IJC) — needs its own kind.
- NHPA §106 water-adjacent fights.
- A monitors watch on DRBC/SRBC docket calendars (would be a genuine new scraper).
