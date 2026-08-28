"""POST /feedback: validation and persistence behaviour.

Uses a fake session in place of get_session so these tests exercise the real
request validation and endpoint logic without needing a Postgres connection.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_session
from app.main import app
from app.models.schema import Feedback

VALID_PAYLOAD = {
    "question": "Can my partner work while I study?",
    "feedback_type": "outside_coverage",
    "comment": "I was looking for partner work rights.",
    "evidence_status": "corpus_gap",
    "answer": "The indexed Operational Manual...",
    "cited_sections": ["U8.20"],
}


class FakeSession:
    """Records what the route would have persisted, without a real database."""

    def __init__(self) -> None:
        self.added: list[Feedback] = []

    def add(self, obj: Feedback) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        for obj in self.added:
            if obj.id is None:
                obj.id = len(self.added)

    async def rollback(self) -> None:
        pass

    async def refresh(self, obj: Feedback) -> None:
        pass


@pytest.fixture
def fake_session():
    session = FakeSession()

    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    yield session
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_valid_feedback_is_saved(client, fake_session):
    response = await client.post("/feedback", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "received"
    assert "id" in body

    assert len(fake_session.added) == 1
    saved = fake_session.added[0]
    assert saved.question == VALID_PAYLOAD["question"]
    assert saved.feedback_type == "outside_coverage"
    assert saved.status == "new"


async def test_invalid_feedback_type_is_rejected(client, fake_session):
    payload = {**VALID_PAYLOAD, "feedback_type": "not_a_real_type"}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 422
    assert fake_session.added == []


async def test_missing_question_is_rejected(client, fake_session):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "question"}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 422
    assert fake_session.added == []


async def test_blank_question_is_rejected(client, fake_session):
    payload = {**VALID_PAYLOAD, "question": "   "}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 422
    assert fake_session.added == []


async def test_oversized_comment_is_rejected(client, fake_session):
    payload = {**VALID_PAYLOAD, "comment": "x" * 5000}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 422
    assert fake_session.added == []


async def test_client_cannot_set_status(client, fake_session):
    payload = {**VALID_PAYLOAD, "status": "resolved"}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 201
    assert fake_session.added[0].status == "new"


async def test_cited_sections_list_is_saved(client, fake_session):
    payload = {**VALID_PAYLOAD, "cited_sections": ["U13.15", "U6.40"]}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 201
    assert fake_session.added[0].cited_sections == ["U13.15", "U6.40"]


async def test_too_many_cited_sections_is_rejected(client, fake_session):
    payload = {**VALID_PAYLOAD, "cited_sections": [f"U{i}.1" for i in range(11)]}
    response = await client.post("/feedback", json=payload)

    assert response.status_code == 422
    assert fake_session.added == []
