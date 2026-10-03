"""Two-stage search on qdrant-client's local mode (CPU). Local mode ignores quantization, so the
binary first stage runs as an exact scan here; Task 5.3 measures the real binary scan on the server."""

import pytest
import torch
from qdrant_client import QdrantClient, models

from pagesight.config import ROOT
from pagesight.data.vidore import Page
from pagesight.index.qdrant_store import create_collection, index_pages
from pagesight.search.two_stage import two_stage

pytestmark = pytest.mark.filterwarnings("ignore:Local mode performs exact")

E = torch.eye(128)
# Query [e0, e1]. Exact MaxSim: page 1 = 2.0 > page 2 = 1.4 > page 3 = 0. The mean-pooled first
# stage (pooled vector . mean query (0.5, 0.5)) ranks page 2 (0.7) above page 1 (0.25).
VECTORS = {
    "toy-1": E[[0, 1, 2, 3]],
    "toy-2": (0.6 * E[0] + 0.8 * E[1])[None],
    "toy-3": E[[2]],
}
QUERY = E[[0, 1]]


@pytest.fixture
def client() -> QdrantClient:
    client = QdrantClient(":memory:")
    create_collection(client, "toy", binary=True)
    pages = [
        Page(pid, ROOT / "data" / "toy" / "pages" / f"{pid}.png", "", "doc", 0)
        for pid in VECTORS
    ]
    index_pages(client, "toy", pages, VECTORS, batch_size=8)
    return client


def test_mean_first_stage_passes_only_n_candidates(client):
    assert two_stage(client, "toy", QUERY, k=1, first_stage="mean", n=1) == [2]
    assert two_stage(client, "toy", QUERY, k=1, first_stage="mean", n=2) == [1]


def test_candidates_are_reranked_by_exact_maxsim(client):
    assert two_stage(client, "toy", QUERY, k=2, first_stage="mean", n=2) == [1, 2]


def test_binary_first_stage_returns_the_exact_order_in_local_mode(client):
    assert two_stage(client, "toy", QUERY, k=3, first_stage="binary", n=2) == [1, 2, 3]


def test_no_first_stage_scans_every_page_with_exact_maxsim(client):
    # the pooled vectors alone would rank page 2 first
    assert two_stage(client, "toy", QUERY, k=3, first_stage="none") == [1, 2, 3]


@pytest.mark.parametrize("first_stage", ["mean", "binary", "none"])
def test_filter_limits_both_stages_to_the_given_pages(client, first_stage):
    allowed = models.Filter(must=[models.HasIdCondition(has_id=[2, 3])])
    hits = two_stage(client, "toy", QUERY, 3, first_stage, n=3, query_filter=allowed)
    assert hits == [2, 3]


def test_unknown_first_stage_is_rejected(client):
    with pytest.raises(ValueError, match="first stage"):
        two_stage(client, "toy", QUERY, k=3, first_stage="pooled", n=2)
