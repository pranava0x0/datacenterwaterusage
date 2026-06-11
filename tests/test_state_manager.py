"""Tests for storage/state_manager.py — the SQLite resumability layer.

This module is the backbone of CLAUDE.md § 2 (caching and re-run skipping):
every scraper consults it to decide whether a document needs fetching. It was
the last untested storage module (gap found in the 2026-06-10 test audit).
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from storage.state_manager import StateManager


@pytest_asyncio.fixture
async def manager(tmp_path):
    m = StateManager(str(tmp_path / "state" / "scraper_state.db"))
    await m.initialize()
    return m


class TestStateManager:
    @pytest.mark.asyncio
    async def test_initialize_creates_parent_dirs(self, tmp_path):
        # db_path nests in a directory that doesn't exist yet — initialize
        # must create it (scrapers point at data/state/ on first run).
        db = tmp_path / "a" / "b" / "state.db"
        m = StateManager(str(db))
        await m.initialize()
        assert db.exists()

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, manager):
        # Re-running initialize on an existing DB must not raise or wipe state.
        await manager.mark_fetched("epa_echo", "doc-1")
        await manager.initialize()
        assert await manager.is_fetched("epa_echo", "doc-1")

    @pytest.mark.asyncio
    async def test_unknown_doc_is_neither_fetched_nor_processed(self, manager):
        assert not await manager.is_fetched("epa_echo", "nope")
        assert not await manager.is_processed("epa_echo", "nope")

    @pytest.mark.asyncio
    async def test_mark_fetched_roundtrip(self, manager):
        await manager.mark_fetched("epa_echo", "doc-1", local_path="data/downloads/x.pdf")
        assert await manager.is_fetched("epa_echo", "doc-1")
        # Fetched is not processed — extraction still pending.
        assert not await manager.is_processed("epa_echo", "doc-1")

    @pytest.mark.asyncio
    async def test_mark_processed_lifecycle(self, manager):
        await manager.mark_fetched("epa_echo", "doc-1")
        await manager.mark_processed("epa_echo", "doc-1")
        assert await manager.is_processed("epa_echo", "doc-1")
        # Still counts as fetched (is_fetched = "row exists").
        assert await manager.is_fetched("epa_echo", "doc-1")

    @pytest.mark.asyncio
    async def test_mark_processed_without_fetch_is_noop(self, manager):
        # UPDATE on a missing row affects nothing — must not invent state.
        await manager.mark_processed("epa_echo", "ghost")
        assert not await manager.is_processed("epa_echo", "ghost")
        assert not await manager.is_fetched("epa_echo", "ghost")

    @pytest.mark.asyncio
    async def test_scrapers_are_isolated(self, manager):
        # Same document_id under two scrapers are independent rows — the
        # composite primary key is what makes re-runs per-scraper safe.
        await manager.mark_fetched("epa_echo", "doc-1")
        assert not await manager.is_fetched("deq_vwp", "doc-1")

    @pytest.mark.asyncio
    async def test_refetch_resets_processed_status(self, manager):
        # INSERT OR REPLACE on a processed row downgrades it to 'fetched' —
        # this is the adjudicate-toward-newer behavior (CLAUDE.md § 3): a
        # re-downloaded document must be re-extracted.
        await manager.mark_fetched("epa_echo", "doc-1")
        await manager.mark_processed("epa_echo", "doc-1")
        await manager.mark_fetched("epa_echo", "doc-1", local_path="new.pdf")
        assert await manager.is_fetched("epa_echo", "doc-1")
        assert not await manager.is_processed("epa_echo", "doc-1")
