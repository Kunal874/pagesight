"""Qdrant index tests on qdrant-client's in-process local mode: CPU-only, no server needed.
Local mode ignores quantization, so the binary variant is checked on the real server (Task 4.5)."""

import pytest
import torch
from qdrant_client import QdrantClient, models

from pagesight.config import ROOT
from pagesight.data.vidore import Page
from pagesight.index.qdrant_store import create_collection, index_pages

E = torch.eye(128)  # one-hot rows make every score computable by hand
VECTORS = {
    "toy-0": E[[0, 1]],
    # not unit length: Dot and Cosine disagree
    "toy-1": torch.stack([0.5 * E[0], E[1]]),
    "toy-2": E[[2]],
    "toy-3": E[[3, 4, 5]],
    "toy-4": -E[[0]],
}
QUERY = E[[0, 1]].tolist()


def toy_pages() -> list[Page]:
    return [
        Page(f"toy-{i}", ROOT / "data" / "toy" / "pages" / f"{i}.png", "", "doc-1", i)
        for i in range(5)
    ]


@pytest.fixture
def client() -> QdrantClient:
    client = QdrantClient(":memory:")
    create_collection(client, "toy", binary=True)
    return client


def test_maxsim_ranking_uses_dot_product_scores(client):
    index_pages(client, "toy", toy_pages(), VECTORS, batch_size=2)

    hits = client.query_points("toy", query=QUERY, using="patches", limit=5).points

    # toy-0: 1 + 1; toy-1: 0.5 + 1 (Cosine would give 2.0); toy-2/3: 0; toy-4: -1 + 0
    assert [h.score for h in hits] == pytest.approx([2.0, 1.5, 0.0, 0.0, -1.0])
    assert [h.id for h in hits[:2]] == [0, 1] and hits[4].id == 4


def test_point_holds_patches_pooled_mean_and_payload(client):
    index_pages(client, "toy", toy_pages(), VECTORS, batch_size=2)

    point = client.retrieve("toy", [3], with_vectors=True)[0]

    assert point.payload == {
        "subset": "toy",
        "doc_id": "doc-1",
        "page_number": 3,
        "image": "data/toy/pages/3.png",  # relative POSIX path: works on Linux too
    }
    assert point.vector["patches"] == E[[3, 4, 5]].tolist()
    pooled = torch.zeros(128)
    pooled[3:6] = 1 / 3
    assert point.vector["pooled"] == pytest.approx(pooled.tolist())


def test_rerun_skips_pages_already_indexed(client):
    pages = toy_pages()
    assert index_pages(client, "toy", pages[:3], VECTORS, batch_size=2) == 3

    create_collection(client, "toy", binary=True)  # a re-run must not wipe the index
    changed = {**VECTORS, "toy-1": E[[7]]}
    assert index_pages(client, "toy", pages, changed, batch_size=2) == 2

    assert client.count("toy").count == 5
    stored = client.retrieve("toy", [1], with_vectors=True)[0].vector["patches"]
    assert stored == VECTORS["toy-1"].tolist()  # skipped, not re-uploaded


def test_binary_flag_sets_quantization_on_patches_only():
    client = QdrantClient(":memory:")
    create_collection(client, "binary", binary=True)
    create_collection(client, "plain", binary=False)

    def quantization(name: str, vector: str):
        vectors = client.get_collection(name).config.params.vectors
        return vectors[vector].quantization_config

    assert isinstance(quantization("binary", "patches"), models.BinaryQuantization)
    assert quantization("binary", "pooled") is None
    assert quantization("plain", "patches") is None
