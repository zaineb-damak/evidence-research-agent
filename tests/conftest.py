"""Shared test doubles: a LangChain-native fake chat model, a deterministic
embeddings object, and a fake connector that returns content directly.

The fake chat model implements `with_structured_output(include_raw=True)` so the
production chains (prompt | with_structured_output | retry) run unchanged against
it. A responder maps the rendered prompt text to the JSON payload the model
"returns"; routing mirrors the substrings the real system prompts contain.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import pytest
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda

from src.llm.base import StructuredLLM
from src.llm.chains import JSON_MODE
from src.models.schemas import SourceType
from src.sources.base import RawResult

FAKE_MODEL_NAME = "fake-model"
FAKE_TOKENS_IN = 10
FAKE_TOKENS_OUT = 10


class FakeChatModel(BaseChatModel):
    """A chat model that returns scripted JSON and supports structured output."""

    responder: Any  # Callable[[str], dict]
    tokens_in: int = FAKE_TOKENS_IN
    tokens_out: int = FAKE_TOKENS_OUT

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def _generate(self, messages: list[BaseMessage], stop=None, run_manager=None, **kwargs):
        prompt_text = "\n".join(str(message.content) for message in messages)
        payload = self.responder(prompt_text)
        message = AIMessage(
            content=json.dumps(payload),
            usage_metadata={
                "input_tokens": self.tokens_in,
                "output_tokens": self.tokens_out,
                "total_tokens": self.tokens_in + self.tokens_out,
            },
        )
        return ChatResult(generations=[ChatGeneration(message=message)])

    def with_structured_output(self, schema, *, include_raw: bool = False, **kwargs) -> Runnable:
        def parse(message: AIMessage):
            parsed = schema.model_validate_json(message.content)
            if include_raw:
                return {"raw": message, "parsed": parsed, "parsing_error": None}
            return parsed

        return self | RunnableLambda(parse)


def structured_llm(
    responder: Any, *, retry_attempts: int = 0, model: str = FAKE_MODEL_NAME
) -> StructuredLLM:
    """Wrap a responder in a StructuredLLM the agents can consume."""
    return StructuredLLM(
        chat_model=FakeChatModel(responder=responder),
        model=model,
        method=JSON_MODE,
        retry_attempts=retry_attempts,
    )


def fixed_response(payload: dict) -> Any:
    """A responder that ignores the prompt and always returns `payload`."""
    return lambda _prompt_text: payload


def _first_passage_id(prompt_text: str) -> str:
    match = re.search(r"passage_id=(\S+)", prompt_text)
    return match.group(1) if match else "unknown"


def pipeline_response(prompt_text: str) -> dict:
    """Route on the system-prompt phrases the real prompts contain."""
    if "research planner" in prompt_text:
        return {"sub_questions": ["What context length does Model X support?"]}
    if "extract factual claims" in prompt_text:
        return {
            "claims": [
                {
                    "claim": "Model X supports 128K context.",
                    "passage_id": _first_passage_id(prompt_text),
                    "evidence_snippet": "Model X supports a context length of 128K tokens.",
                    "entities": [{"name": "Model X", "type": "model"}],
                }
            ]
        }
    if "executive summary" in prompt_text:
        return {"executive_summary": "Model X supports a 128K context window."}
    if "reconcile two candidate claims" in prompt_text:
        return {"relation": "same", "reason": "same fact, reworded"}
    if "evidence snippet supports the claim" in prompt_text:
        return {"entailment": "entailed"}
    return {}


class DeterministicEmbeddings(Embeddings):
    """Hashing embedder: stable vectors without a network call."""

    dim = 16

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self.dim
            vector[bucket] += 1.0
        return vector


class ConstantEmbeddings(Embeddings):
    """Returns the same vector for any text, forcing maximal similarity."""

    def __init__(self, vector: list[float]):
        self._vector = vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(self._vector) for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return list(self._vector)


class TableEmbeddings(Embeddings):
    """Maps exact text -> a caller-defined vector for controllable similarities."""

    def __init__(self, table: dict[str, list[float]]):
        self._table = table

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._table[text] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._table[text]


class FakeConnector:
    source_type = SourceType.WEB

    def search(self, query: str, limit: int) -> list[RawResult]:
        return [
            RawResult(
                url="https://docs.example.com/model-x",
                title="Model X Documentation",
                content=(
                    "Model X supports a context length of 128K tokens. "
                    "It also supports native tool calling and multiple languages."
                ),
                source_type=SourceType.DOCUMENTATION,
                domain="docs.example.com",
            )
        ]


@pytest.fixture
def fake_llm() -> StructuredLLM:
    return structured_llm(pipeline_response)


@pytest.fixture
def fake_embedder() -> DeterministicEmbeddings:
    return DeterministicEmbeddings()


@pytest.fixture
def fake_connectors() -> dict:
    return {SourceType.WEB: FakeConnector()}


def make_deps(llm, embeddings, connectors, passage_index=None, graph_store=None):
    """Build Deps with in-memory store doubles for tests.

    Returns (deps, passage_index, graph_store) so a test can inspect the same
    store instances the pipeline wrote to (e.g. the graph the API will read).
    """
    from src.retrieval.index import InMemoryPassageIndex
    from src.stores.graph import InMemoryGraphStore
    from src.workflows.nodes import Deps

    passage_index = passage_index or InMemoryPassageIndex()
    graph_store = graph_store or InMemoryGraphStore()
    deps = Deps(
        llm=llm,
        embeddings=embeddings,
        connectors=connectors,
        passage_index=passage_index,
        graph_store=graph_store,
    )
    return deps, passage_index, graph_store
