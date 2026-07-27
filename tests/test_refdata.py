"""Tests for the refdata package: loaders, registry, taxonomies, integrity.

The integrity tests here are the whole reason the package exists. A cross-
reference between two curated datasets is an id in a JSON file; nothing but a
test stops it from pointing at a record that was renamed or never existed, and
the resulting dead link is invisible in review. These walk every edge type in
one pass, so a new dataset joins the guarantee by adding one clause to
``refdata.integrity.iter_edges`` rather than a new bespoke test.
"""

from __future__ import annotations

import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from refdata import integrity, loaders, registry, taxonomies


class TestLoaders:
    """The loaders moved out of dashboard.py must behave identically."""

    def test_all_seven_datasets_load_non_empty(self):
        assert loaders.load_legislation()["bills"]
        assert loaders.load_company_water_claims()["claims"]
        assert loaders.load_cwa_investigations()["cases"]
        assert loaders.load_water_authorities()["readings"]
        assert loaders.load_dc_water_conflicts()["sites"]
        assert loaders.load_water_news()["items"]
        assert loaders.load_water_solutions()["categories"]

    def test_missing_file_returns_empty_payload(self, tmp_path):
        """A missing dataset renders an empty section, never a crash."""
        absent = tmp_path / "nope.json"
        assert loaders.load_legislation(absent) == {"last_updated": None, "bills": []}
        assert loaders.load_cwa_investigations(absent)["cases"] == []
        assert loaders.load_water_authorities(absent)["statutes"] == {}

    def test_signature_busts_cache_on_change(self, tmp_path):
        """Caching is keyed on (mtime_ns, size), not a clock — an edit must be
        picked up on the very next call, since curation edits and reruns
        interleave constantly during an authoring session."""
        p = tmp_path / "news.json"
        p.write_text(json.dumps({"items": [{"id": "a"}]}))
        assert [i["id"] for i in loaders.load_water_news(p)["items"]] == ["a"]

        p.write_text(json.dumps({"items": [{"id": "a"}, {"id": "b"}]}))
        os.utime(p, ns=(0, 10**9))  # force a distinct mtime on fast filesystems
        assert [i["id"] for i in loaders.load_water_news(p)["items"]] == ["a", "b"]

    def test_file_signature_of_missing_file(self):
        assert loaders.file_signature("/nonexistent/path/x.json") == (0, 0)

    def test_no_streamlit_in_refdata(self):
        """The purity rule that lets build_site.py, scripts/ and tests import
        this layer without dragging in a Streamlit runtime."""
        import pathlib

        pkg = pathlib.Path(loaders.__file__).parent
        for module in pkg.glob("*.py"):
            assert "import streamlit" not in module.read_text(), module.name


class TestRegistry:
    def test_every_record_registered(self):
        reg = registry.build_registry()
        kinds = {}
        for ref in reg.values():
            kinds[ref.kind] = kinds.get(ref.kind, 0) + 1
        # One entry per record in each dataset, nothing silently skipped.
        assert kinds["instrument"] == len(loaders.load_legislation()["bills"])
        assert kinds["case"] == len(loaders.load_cwa_investigations()["cases"])
        assert kinds["site"] == len(loaders.load_dc_water_conflicts()["sites"])
        assert kinds["reading"] == len(loaders.load_water_authorities()["readings"])
        assert kinds["claim"] == len(loaders.load_company_water_claims()["claims"])
        assert kinds["news"] == len(loaders.load_water_news()["items"])
        assert kinds["solution"] == sum(
            len(c["solutions"]) for c in loaders.load_water_solutions()["categories"]
        )

    def test_no_id_collisions(self):
        """Ids are assumed globally unique across datasets; if two records ever
        claim one, every link to it silently points at whichever loaded first."""
        assert registry.registry_collisions() == []

    def test_anchors_match_rendered_ids(self):
        """The registry's anchor must be the anchor the builders actually emit,
        or cross-tab links scroll to nothing."""
        reg = registry.build_registry()
        case_id = loaders.load_cwa_investigations()["cases"][0]["case_id"]
        site_id = loaders.load_dc_water_conflicts()["sites"][0]["site_id"]
        reading_id = loaders.load_water_authorities()["readings"][0]["reading_id"]
        assert reg[case_id].anchor == f"cwa-{case_id}"
        assert reg[site_id].anchor == f"site-{site_id}"
        assert reg[reading_id].anchor == f"reading-{reading_id}"

    def test_bill_anchor_slugging(self):
        assert registry.bill_anchor("VA HB 496 / SB 553") == "bill-va-hb-496-sb-553"
        assert registry.bill_anchor("US EO 14318") == "bill-us-eo-14318"

    def test_bill_anchor_matches_dashboard(self):
        """dashboard._bill_anchor is now this function; the alias must hold so
        existing anchors in the committed page stay stable."""
        import dashboard as dash

        for bill in loaders.load_legislation()["bills"]:
            assert dash._bill_anchor(bill["bill_id"]) == registry.bill_anchor(
                bill["bill_id"]
            )

    def test_every_kind_has_a_tab(self):
        for ref in registry.build_registry().values():
            assert ref.tab in {
                "legislation", "cwa", "issues", "news", "solutions", "sources"
            }

    def test_resolve_unknown_id(self):
        assert registry.resolve("not-a-real-id-2026") is None


class TestIntegrity:
    def test_no_dangling_edges(self):
        dangling = integrity.dangling_edges()
        assert not dangling, "\n".join(
            f"{src} --{kind}--> {target} (no such record)"
            for src, target, kind in dangling
        )

    def test_no_miskinded_edges(self):
        """A resolvable id pointing at the wrong kind of record — e.g. a
        `case.authorities` entry naming a site — renders a plausible link to
        the wrong place, which is worse than a dead one."""
        bad = integrity.miskinded_edges()
        assert not bad, "\n".join(
            f"{src} --{kind}--> {target} resolves to a {actual}, not {sorted(integrity.EDGE_TARGET_KINDS[kind])}"
            for src, target, kind, actual in bad
        )

    def test_claim_case_edges_are_symmetric(self):
        assert integrity.asymmetric_claim_case_edges() == []

    def test_existing_edges_are_actually_walked(self):
        """Guards the guard: if iter_edges stopped finding the edge types the
        datasets already use, the integrity tests above would pass vacuously."""
        kinds = {kind for _, _, kind in integrity.iter_edges()}
        for expected in (
            "case.authorities",
            "reading.example_case_ids",
            "site.applicable_readings",
            "site.related_case_ids",
        ):
            assert expected in kinds, f"{expected} edges are no longer being walked"

    def test_every_edge_kind_is_declared(self):
        """Every edge iter_edges emits needs a target-kind rule, or
        miskinded_edges silently skips it."""
        for kind in {k for _, _, k in integrity.iter_edges()}:
            assert kind in integrity.EDGE_TARGET_KINDS


class TestExplicitCrossRefs:
    """Spec 0.4 — ids instead of prose substring-matching."""

    @staticmethod
    def _entries_with_targets():
        entries = [
            e for e in loaders.load_water_news()["items"] if e.get("cross_ref_targets")
        ]
        entries += [
            s
            for c in loaders.load_water_solutions()["categories"]
            for s in c["solutions"]
            if s.get("cross_ref_targets")
        ]
        return entries

    def test_dataset_actually_uses_explicit_targets(self):
        """If the migration were reverted, every assertion below would pass
        vacuously on an empty list."""
        assert len(self._entries_with_targets()) >= 25

    def test_one_link_per_declared_target(self):
        """The contract that makes the explicit path trustworthy: a declared
        target always renders, whether or not its label appears in the prose."""
        import re as _re

        import dashboard as dash

        for entry in self._entries_with_targets():
            rendered = dash._crossref_html(entry, "test-crossref")
            assert len(_re.findall(r"<a ", rendered)) == len(
                entry["cross_ref_targets"]
            ), entry.get("id")

    def test_links_point_at_registry_anchors(self):
        import dashboard as dash

        reg = registry.build_registry()
        for entry in self._entries_with_targets():
            rendered = dash._crossref_html(entry, "test-crossref")
            for target in entry["cross_ref_targets"]:
                assert f'href="#{reg[target].anchor}"' in rendered, (
                    entry.get("id"),
                    target,
                )

    def test_legacy_prose_path_still_works(self):
        """Entries that point at a scraper or a tab section — not a record —
        have no id to declare and must keep rendering."""
        import dashboard as dash

        legacy = {
            "cross_ref_tab": "legislation",
            "cross_ref_note": "VA HB 496 / SB 553 tracked in Legislation tab",
        }
        out = dash._crossref_html(legacy, "test-crossref")
        assert 'href="#bill-va-hb-496-sb-553"' in out

    def test_entry_without_any_crossref_renders_nothing(self):
        import dashboard as dash

        assert dash._crossref_html({"id": "x"}, "test-crossref") == ""

    def test_unresolvable_target_is_dropped_not_dead_linked(self):
        """A bad id must not become an anchor to nowhere. The integrity test
        is what fails the build; the renderer just refuses to emit it."""
        import dashboard as dash

        out = dash._crossref_html(
            {"id": "x", "cross_ref_note": "note", "cross_ref_targets": ["no-such-id"]},
            "test-crossref",
        )
        assert out == ""


class TestPolicyInstrumentSchema:
    """Spec B1 — legislation.json holds policy *instruments*, not just bills."""

    @staticmethod
    def _bills():
        return loaders.load_legislation()["bills"]

    def test_every_entry_has_a_valid_instrument_type(self):
        for entry in self._bills():
            itype = entry.get("instrument_type")
            assert itype in taxonomies.INSTRUMENT_TYPE_LABELS, (
                entry.get("bill_id"),
                itype,
            )

    def test_federal_executive_layer_present(self):
        """The gap this spec exists to close: EO 14318 drove the NWP 39
        reissuance the tracker already records, so recording the consequence
        without the cause left the federal permitting story unexplained."""
        ids = {e["bill_id"] for e in self._bills()}
        assert "US EO 14318" in ids
        assert "NY EO 62" in ids
        types = {e["instrument_type"] for e in self._bills()}
        assert "executive-order" in types
        assert "commission-docket" in types

    def test_commission_dockets_carry_a_timeline(self):
        """A docket with no filing or order dates is indistinguishable from a
        rumour; the timeline is what makes it trackable."""
        for entry in self._bills():
            if entry["instrument_type"] == "commission-docket":
                assert entry.get("timeline"), entry["bill_id"]

    def test_principles_are_in_the_closed_taxonomy(self):
        for entry in self._bills():
            for principle in entry.get("general_principles", []):
                assert (
                    principle["tag"] in taxonomies.LEGISLATION_PRINCIPLE_DESCRIPTIONS
                ), (entry["bill_id"], principle["tag"])

    def test_permitting_acceleration_is_used(self):
        """Taxonomy values ship with their data — an unused value means either
        the value or the records went missing."""
        tags = {
            p["tag"] for e in self._bills() for p in e.get("general_principles", [])
        }
        assert "Permitting acceleration" in tags

    def test_no_duplicate_instruments(self):
        """Found by Codex during PR review. The dataset carried the Durbin
        transparency act twice — once as a 'number TBD' stub from the press
        release, once as the confirmed S. 4213 — so the tracker double-counted
        a federal bill. Same title + sponsor + jurisdiction is one instrument."""
        seen: dict[tuple, str] = {}
        for entry in self._bills():
            key = (
                entry.get("title", "").strip().lower(),
                entry.get("sponsor", "").strip().lower(),
                entry.get("jurisdiction", "").strip().lower(),
            )
            if not any(key):
                continue
            assert key not in seen, (
                f"{entry['bill_id']} duplicates {seen[key]} "
                f"(same title, sponsor and jurisdiction)"
            )
            seen[key] = entry["bill_id"]

    def test_monitored_bills_use_a_status_aware_kind(self):
        """A Federal Register keyword search cannot observe Senate status. A
        bill with a known number should be watched via a legislative source."""
        for entry in self._bills():
            monitor = entry.get("monitor")
            if monitor and monitor["kind"] == "federal-register":
                assert not entry["bill_id"].startswith(("US S. ", "US HR ")), (
                    f"{entry['bill_id']} has a bill number — watch it via legiscan"
                )

    def test_unverified_entries_explain_what_to_recheck(self):
        """Fail-closed curation: an entry that isn't fully sourced must say so
        in prose a curator can act on, not just carry a false flag."""
        for entry in self._bills():
            if entry.get("verified") is False:
                assert entry.get("status_detail"), entry["bill_id"]

    def test_new_entries_have_sources(self):
        for entry in self._bills():
            assert entry.get("source_url", "").startswith("http"), entry["bill_id"]

    def test_implements_edges_resolve(self):
        """Covered generically by the integrity suite; asserted here so the
        specific chain this spec built (rule -> enabling act, EO -> blueprint)
        is pinned."""
        by_id = {e["bill_id"]: e for e in self._bills()}
        assert "VA HB 496 / SB 553" in by_id[
            "VA DEQ waterworks data-center reporting regulations"
        ]["implements"]
        assert "US EO 14318" in by_id["QTS Richmond Technology Park DC5 (FAST-41)"][
            "implements"
        ]
        assert "USACE-NWP39-DataCenters-2026" in by_id["US EO 14318"][
            "related_case_ids"
        ]


class TestIssueTypes:
    """Spec A1 — a closed classification over the conflict registry."""

    @staticmethod
    def _sites():
        return loaders.load_dc_water_conflicts()["sites"]

    def test_every_site_classified(self):
        for site in self._sites():
            tags = site.get("issue_types")
            assert tags, site["site_id"]
            assert len(tags) <= 3, f"{site['site_id']} has {len(tags)} tags; cap is 3"

    def test_tags_are_in_the_closed_taxonomy(self):
        for site in self._sites():
            for tag in site["issue_types"]:
                assert tag in taxonomies.ISSUE_TYPE_LABELS, (site["site_id"], tag)

    def test_no_duplicate_tags_on_a_site(self):
        for site in self._sites():
            assert len(site["issue_types"]) == len(set(site["issue_types"])), site["site_id"]

    def test_every_taxonomy_value_is_used(self):
        """An issue type nothing is classified as becomes an empty filter —
        values ship with their data, so an unused one means a site is missing
        or the value was added early."""
        used = {tag for site in self._sites() for tag in site["issue_types"]}
        assert set(taxonomies.ISSUE_TYPE_LABELS) == used, (
            f"unused: {sorted(set(taxonomies.ISSUE_TYPE_LABELS) - used)}"
        )

    def test_classification_carries_its_justification(self):
        """Each label has to be checkable against the record it labels,
        otherwise a wrong classification is invisible in review."""
        for site in self._sites():
            assert len(site.get("issue_types_rationale", "")) > 40, site["site_id"]


class TestClassificationChips:
    """The P1/A1 data has to reach the page, or it is only half-delivered."""

    def test_non_bill_instruments_get_a_chip(self):
        import dashboard as dash

        for bill in loaders.load_legislation()["bills"]:
            out = dash._build_bill_card_html(bill)
            itype = bill["instrument_type"]
            if itype == "bill":
                # Bills are the default; a chip on all 50 would be noise.
                assert 'class="instrument-pill"' not in out, bill["bill_id"]
            else:
                assert 'class="instrument-pill"' in out, bill["bill_id"]
                assert taxonomies.INSTRUMENT_TYPE_LABELS[itype] in out, bill["bill_id"]

    def test_conflict_cards_show_every_issue_type(self):
        import dashboard as dash

        readings_by_id = dash._readings_by_id()
        case_ids = {c["case_id"] for c in loaders.load_cwa_investigations()["cases"]}
        for site in loaders.load_dc_water_conflicts()["sites"]:
            out = dash._build_conflict_site_html(site, readings_by_id, case_ids)
            assert out.count('class="issue-pill"') == len(site["issue_types"]), site["site_id"]
            for tag in site["issue_types"]:
                # Labels are escaped on the way out ('Secrecy & FOIA fights'
                # becomes '&amp;'), so compare against the escaped form.
                assert html.escape(taxonomies.ISSUE_TYPE_LABELS[tag]) in out, (
                    site["site_id"],
                    tag,
                )

    def test_sites_carry_filterable_issue_data(self):
        """The static site filters on data-issues; without it every site shows
        under every filter selection, which looks like a working filter."""
        import dashboard as dash

        readings_by_id = dash._readings_by_id()
        for site in loaders.load_dc_water_conflicts()["sites"]:
            out = dash._build_conflict_site_html(site, readings_by_id, set())
            assert 'class="bill-card dc-site"' in out, site["site_id"]
            expected = " ".join(site["issue_types"])
            assert f'data-issues="{expected}"' in out, site["site_id"]

    def test_chip_styles_exist_for_both_surfaces(self):
        """One stylesheet feeds the Streamlit app and the static site; a chip
        class with no rule renders as unstyled text on both."""
        import pathlib

        css = (
            pathlib.Path(loaders.BASE_DIR) / "assets" / "components.css"
        ).read_text()
        assert ".instrument-pill" in css
        assert ".issue-pill" in css


class TestAuthorityFamilies:
    """Spec C1 — the registry speaks doctrine, not just federal statutes."""

    @staticmethod
    def _statutes():
        return loaders.load_water_authorities()["statutes"]

    def test_every_family_declares_a_kind(self):
        """A federal statute and a state common-law doctrine read completely
        differently — no agency, no permit, litigated in state court — and the
        UI says which the user is looking at."""
        for code, meta in self._statutes().items():
            assert meta.get("kind") in taxonomies.AUTHORITY_KIND_LABELS, (code, meta.get("kind"))

    def test_doctrine_families_present(self):
        """The gap C1 exists to close: the Memphis fight turns on interstate
        aquifer apportionment and the Georgia one on state groundwater law,
        neither of which the five federal statutes can express."""
        codes = set(self._statutes())
        assert {"EQAP", "PTD", "GW"} <= codes

    def test_non_federal_families_are_marked_as_such(self):
        kinds = {meta["kind"] for meta in self._statutes().values()}
        assert kinds - {"federal-statute"}, "no non-federal family is registered"

    def test_doctrine_anchors_reach_tracked_fact_patterns(self):
        """A precedent that names no tracked conflict is a history entry. The
        anchors must point at live data-center matters in the corpus, which is
        what makes the registry a tool rather than a reading list."""
        cases = {c["case_id"]: c for c in loaders.load_cwa_investigations()["cases"]}
        readings = loaders.load_water_authorities()["readings"]
        doctrine = [r for r in readings if r["statute"] in {"EQAP", "PTD", "GW"}]
        assert doctrine
        for reading in doctrine:
            for case_id in reading["example_case_ids"]:
                analogs = cases[case_id].get("analogous_cases", [])
                assert analogs, f"{case_id} names no tracked fact pattern"
                assert any(
                    cases[a]["category"] in {"datacenter", "adjacent"} for a in analogs
                ), f"{case_id}'s analogs are all precedent — none is a live matter"


class TestTaxonomyConstants:
    def test_dashboard_reexports_are_the_same_objects(self):
        """dashboard.py re-exports rather than redefines, so there is exactly
        one taxonomy in the process no matter which module a caller imports."""
        import dashboard as dash

        for name in (
            "CWA_CASE_TYPE_LABELS",
            "LEGISLATION_PRINCIPLE_DESCRIPTIONS",
            "WATER_STATUTE_ORDER",
            "NEWS_TAG_LABELS",
            "COLORS",
        ):
            assert getattr(dash, name) is getattr(taxonomies, name), name

    def test_statute_order_and_colors_agree(self):
        assert set(taxonomies.WATER_STATUTE_ORDER) == set(
            taxonomies.WATER_STATUTE_COLORS
        )

    def test_issue_types_have_descriptions(self):
        assert set(taxonomies.ISSUE_TYPE_LABELS) == set(
            taxonomies.ISSUE_TYPE_DESCRIPTIONS
        )

    def test_instrument_types_have_colors(self):
        assert set(taxonomies.INSTRUMENT_TYPE_LABELS) == set(
            taxonomies.INSTRUMENT_TYPE_COLORS
        )


class TestOutcomeTypes:
    """Spec C3 piece 2 — what actually happened, not just what it was about."""

    @staticmethod
    def _cases():
        return loaders.load_cwa_investigations()["cases"]

    def test_every_case_has_an_outcome_type(self):
        for case in self._cases():
            assert case.get("outcome_type"), case["case_id"]

    def test_values_are_in_the_closed_taxonomy(self):
        for case in self._cases():
            for t in case["outcome_type"]:
                assert t in taxonomies.OUTCOME_TYPE_LABELS, (case["case_id"], t)

    def test_no_duplicates(self):
        for case in self._cases():
            types = case["outcome_type"]
            assert len(types) == len(set(types)), case["case_id"]

    def test_every_taxonomy_value_is_used(self):
        used = {t for c in self._cases() for t in c["outcome_type"]}
        assert set(taxonomies.OUTCOME_TYPE_LABELS) == used, (
            f"unused: {sorted(set(taxonomies.OUTCOME_TYPE_LABELS) - used)}"
        )

    def test_undecided_matters_are_tagged_pending(self):
        """These records open with PENDING when nothing has been decided. The
        classifier reads prose, and an undecided matter's prose describes what
        is *proposed* — so without this the proposal reads as the outcome."""
        for case in self._cases():
            if case["outcome"].strip().lower().startswith("pending"):
                assert "pending-undecided" in case["outcome_type"], case["case_id"]

    def test_negated_enforcement_is_not_recorded_as_enforcement(self):
        """'No formal NOV or consent order issued' must not yield a consent
        decree. Phrase matching cannot see negation; the classifier strips
        negated clauses, and this is the regression guard."""
        by_id = {c["case_id"]: c for c in self._cases()}
        for case_id in ("Nscale-MasonCounty-WV-2026", "Meta-MorganCo-GA-investigation-2026"):
            if case_id in by_id:
                types = by_id[case_id]["outcome_type"]
                assert "consent-decree" not in types, case_id
                assert "monetary-penalty" not in types, case_id


class TestClaimLifecycle:
    """Spec A2 — made → assessed → challenged, not just a verdict."""

    @staticmethod
    def _claims():
        return loaders.load_company_water_claims()["claims"]

    def test_every_claim_has_a_type(self):
        for claim in self._claims():
            assert claim.get("claim_type") in taxonomies.CLAIM_TYPE_LABELS, claim["id"]

    def test_every_claim_type_is_used(self):
        used = {c["claim_type"] for c in self._claims()}
        assert set(taxonomies.CLAIM_TYPE_LABELS) == used, (
            f"unused: {sorted(set(taxonomies.CLAIM_TYPE_LABELS) - used)}"
        )

    def test_litigated_status_is_available_and_used(self):
        """The value exists because a claim became a cause of action; if no
        claim carries it, either the value or the AWS suit went missing."""
        assert "litigated" in taxonomies.DELIVERED_STATUS_COLORS
        statuses = {
            (c.get("delivered") or {}).get("status") for c in self._claims()
        }
        assert "litigated" in statuses

    def test_challenged_claims_name_a_real_case(self):
        """Covered generically by the integrity suite; pinned here because
        this edge is the point of the spec."""
        challenged = [c for c in self._claims() if c.get("challenged_in")]
        assert challenged, "no claim is recorded as challenged"
        reg = registry.build_registry()
        for claim in challenged:
            for case_id in claim["challenged_in"]:
                assert reg[case_id].kind == "case", (claim["id"], case_id)

    def test_a_litigated_claim_is_also_flagged_in_its_assessment(self):
        """A claim can be challenged without the assessment saying so, which
        would show the badge and a stale 'partial' verdict side by side."""
        for claim in self._claims():
            if claim.get("challenged_in"):
                assert (claim.get("delivered") or {}).get("status") == "litigated", (
                    claim["id"]
                )

    def test_related_sites_resolve_to_sites(self):
        reg = registry.build_registry()
        for claim in self._claims():
            for site_id in claim.get("related_site_ids", []):
                assert reg[site_id].kind == "site", (claim["id"], site_id)


class TestSiteDoctrineMappings:
    """Spec C3 piece 1 — the join from doctrine to tracked fact pattern."""

    @staticmethod
    def _readings():
        return {
            r["reading_id"]: r
            for r in loaders.load_water_authorities()["readings"]
        }

    @classmethod
    def _doctrine_ids(cls):
        federal = {"CWA", "SDWA", "TSCA", "RCRA", "RHA"}
        return {
            rid
            for rid, r in cls._readings().items()
            if r["statute"] not in federal
        }

    def test_doctrine_registry_actually_reaches_sites(self):
        """Before this spec the 12 doctrine families existed and no site
        pointed at any of them — the engine was built and unplugged."""
        doctrine = self._doctrine_ids()
        sites = loaders.load_dc_water_conflicts()["sites"]
        mapped = [
            s
            for s in sites
            if any(m["reading_id"] in doctrine for m in s["applicable_readings"])
        ]
        assert len(mapped) >= 18, f"only {len(mapped)} of {len(sites)} sites mapped"

    def test_every_doctrine_family_reaches_some_site(self):
        """A family nobody can reach is a reading list, not a tool."""
        readings = self._readings()
        doctrine = self._doctrine_ids()
        reached = {
            readings[m["reading_id"]]["statute"]
            for s in loaders.load_dc_water_conflicts()["sites"]
            for m in s["applicable_readings"]
            if m["reading_id"] in doctrine
        }
        expected = {readings[rid]["statute"] for rid in doctrine}
        assert expected == reached, f"unreached: {sorted(expected - reached)}"

    def test_negative_mappings_exist_and_are_marked(self):
        """Knowing where a doctrine fails is product-valuable, but it must
        never be mistaken for exposure."""
        negatives = [
            m
            for s in loaders.load_dc_water_conflicts()["sites"]
            for m in s["applicable_readings"]
            if m.get("reaches") is False
        ]
        assert len(negatives) >= 4
        for m in negatives:
            assert len(m.get("how", "")) > 80

    def test_negative_mappings_render_under_their_own_heading(self):
        import dashboard as dash

        readings_by_id = dash._readings_by_id()
        case_ids = {c["case_id"] for c in loaders.load_cwa_investigations()["cases"]}
        for site in loaders.load_dc_water_conflicts()["sites"]:
            negatives = [
                m for m in site["applicable_readings"] if m.get("reaches") is False
            ]
            out = dash._build_conflict_site_html(site, readings_by_id, case_ids)
            heading = "Doctrines that do NOT reach this site"
            assert (heading in out) == bool(negatives), site["site_id"]
            assert out.count("cwa-pathway-negative") == len(negatives), site["site_id"]

    def test_mapping_copy_stays_modal(self):
        """The tracker maps exposure; it does not predict outcomes. Flag the
        assertive constructions that would turn a mapping into a prediction."""
        banned = ("will win", "will succeed", "should sue", "is liable", "will be liable")
        for site in loaders.load_dc_water_conflicts()["sites"]:
            for m in site["applicable_readings"]:
                low = m.get("how", "").lower()
                for phrase in banned:
                    assert phrase not in low, (site["site_id"], m["reading_id"], phrase)


class TestDoctrineMatrixAndOutcomeNote:
    """Spec C3 piece 3 + the matrix panel — both derived, never stored."""

    @staticmethod
    def _ctx():
        import dashboard as dash

        return (
            loaders.load_dc_water_conflicts()["sites"],
            dash._readings_by_id(),
            {c["case_id"]: c for c in loaders.load_cwa_investigations()["cases"]},
        )

    def test_matrix_covers_every_site_and_family(self):
        import dashboard as dash

        sites, readings_by_id, _ = self._ctx()
        out = dash._build_site_doctrine_matrix_html(sites, readings_by_id)
        assert out
        # One body row per site, and every family that reaches a site is a column.
        assert out.count('<th class="dm-site">') == len(sites)
        families = {
            readings_by_id[m["reading_id"]]["statute"]
            for s in sites
            for m in s["applicable_readings"]
            if m["reading_id"] in readings_by_id
        }
        for family in families:
            assert f">{family}</th>" in out, family

    def test_matrix_cell_counts_equal_mapped_readings(self):
        """The matrix must agree with the cards it summarizes; a count that
        drifts is worse than no matrix."""
        import dashboard as dash
        import re

        sites, readings_by_id, _ = self._ctx()
        out = dash._build_site_doctrine_matrix_html(sites, readings_by_id)
        expected = sum(
            1
            for s in sites
            for m in s["applicable_readings"]
            if m["reading_id"] in readings_by_id and m.get("reaches") is not False
        )
        counted = sum(
            int(n) for n in re.findall(r'class="dm-hit">(\d+)<', out)
        )
        assert counted == expected

    def test_matrix_marks_negatives_distinctly(self):
        import dashboard as dash

        sites, readings_by_id, _ = self._ctx()
        out = dash._build_site_doctrine_matrix_html(sites, readings_by_id)
        negatives = sum(
            1
            for s in sites
            for m in s["applicable_readings"]
            if m.get("reaches") is False
        )
        assert out.count('class="dm-neg"') == negatives

    def test_matrix_site_links_use_registry_anchors(self):
        import dashboard as dash

        sites, readings_by_id, _ = self._ctx()
        out = dash._build_site_doctrine_matrix_html(sites, readings_by_id)
        reg = registry.build_registry()
        for site in sites:
            assert f'href="#{reg[site["site_id"]].anchor}"' in out, site["site_id"]

    def test_outcome_note_excludes_negative_mappings(self):
        """A negative mapping's historical cases are counter-examples. Counting
        them would make 'how comparable matters resolved' describe the wrong
        matters."""
        import dashboard as dash

        sites, _, cases_by_id = self._ctx()
        memphis = next(s for s in sites if s["site_id"] == "xai-colossus-memphis-tn")
        profile = dict(dash._site_outcome_profile(memphis, cases_by_id))
        negative_case_ids = {
            cid
            for m in memphis["applicable_readings"]
            if m.get("reaches") is False
            for cid in m.get("analogous_cases", [])
        }
        assert negative_case_ids, "fixture site has no negative mapping"
        only_negative = negative_case_ids - {
            cid
            for m in memphis["applicable_readings"]
            if m.get("reaches") is not False
            for cid in m.get("analogous_cases", [])
        } - set(memphis.get("related_case_ids", []))
        for cid in only_negative:
            for otype in cases_by_id[cid]["outcome_type"]:
                # The tag may legitimately arrive from a positive mapping too;
                # what must not happen is it arriving ONLY from the negative one.
                contributed_elsewhere = any(
                    otype in cases_by_id[o]["outcome_type"]
                    for m in memphis["applicable_readings"]
                    if m.get("reaches") is not False
                    for o in m.get("analogous_cases", [])
                    if o in cases_by_id
                ) or any(
                    otype in cases_by_id[o]["outcome_type"]
                    for o in memphis.get("related_case_ids", [])
                    if o in cases_by_id
                )
                if not contributed_elsewhere:
                    assert otype not in profile, (cid, otype)

    def test_outcome_note_is_framed_as_history_not_prediction(self):
        import dashboard as dash

        sites, _, cases_by_id = self._ctx()
        rendered = 0
        for site in sites:
            note = dash._build_site_outcome_note_html(site, cases_by_id)
            if not note:
                continue
            rendered += 1
            assert "does not predict" in note, site["site_id"]
            assert "How comparable matters resolved" in note
        assert rendered >= 15
