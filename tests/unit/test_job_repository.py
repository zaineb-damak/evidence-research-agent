"""InMemoryJobRepository.list_by_user: ownership filtering for session history.

Exercises the same contract PostgresJobRepository.list_by_user implements
against Postgres (WHERE owner_user_id = :user_id), without needing a database.
"""

from __future__ import annotations

from src.db.repository import InMemoryJobRepository
from src.models.schemas import ResearchRequest, ResearchStatus

OWNER_A = "user_aaaaaaaaaaaa"
OWNER_B = "user_bbbbbbbbbbbb"


def test_list_by_user_returns_only_that_users_jobs():
    repository = InMemoryJobRepository()
    owned_by_a = repository.create(
        ResearchRequest(question="A's question"), owner_user_id=OWNER_A
    )
    repository.create(ResearchRequest(question="B's question"), owner_user_id=OWNER_B)

    items = repository.list_by_user(OWNER_A)

    assert [item.research_id for item in items] == [owned_by_a.research_id]
    assert items[0].question == "A's question"


def test_list_by_user_excludes_null_owner_jobs():
    repository = InMemoryJobRepository()
    repository.create(ResearchRequest(question="anonymous question"), owner_user_id=None)
    repository.create(ResearchRequest(question="A's question"), owner_user_id=OWNER_A)

    items = repository.list_by_user(OWNER_A)

    assert len(items) == 1
    assert items[0].question == "A's question"

    # A null-owner job never matches any user's history, including one with no
    # real caller (which should never happen from an authenticated route, but
    # the filter must not accidentally treat None == None as a match either).
    assert repository.list_by_user(None) == []


def test_list_by_user_orders_newest_first():
    repository = InMemoryJobRepository()
    first = repository.create(ResearchRequest(question="first"), owner_user_id=OWNER_A)
    second = repository.create(ResearchRequest(question="second"), owner_user_id=OWNER_A)

    items = repository.list_by_user(OWNER_A)

    assert [item.research_id for item in items] == [second.research_id, first.research_id]


def test_update_progress_and_get_progress_snapshot_round_trip():
    repository = InMemoryJobRepository()
    state = repository.create(ResearchRequest(question="Q?"), owner_user_id=OWNER_A)

    repository.update_progress(
        state.research_id,
        status=ResearchStatus.SEARCHING,
        detail={"sources_found": 3},
        error=None,
    )

    snapshot = repository.get_progress_snapshot(state.research_id)
    assert snapshot is not None
    assert snapshot.research_id == state.research_id
    assert snapshot.owner_user_id == OWNER_A
    assert snapshot.status == ResearchStatus.SEARCHING
    assert snapshot.error is None
    assert snapshot.progress_detail == {"sources_found": 3}

    # A later call with error set (and detail omitted) updates status/error
    # without clobbering the last-seen detail.
    repository.update_progress(
        state.research_id, status=ResearchStatus.FAILED, detail=None, error="boom"
    )
    failed_snapshot = repository.get_progress_snapshot(state.research_id)
    assert failed_snapshot is not None
    assert failed_snapshot.status == ResearchStatus.FAILED
    assert failed_snapshot.error == "boom"
    assert failed_snapshot.progress_detail == {"sources_found": 3}


def test_get_progress_snapshot_returns_none_for_unknown_job():
    repository = InMemoryJobRepository()
    assert repository.get_progress_snapshot("nope") is None


def test_update_progress_is_a_no_op_for_unknown_job():
    repository = InMemoryJobRepository()
    # Should not raise, mirroring a Postgres UPDATE that matches zero rows.
    repository.update_progress("nope", status=ResearchStatus.SEARCHING, detail={}, error=None)
