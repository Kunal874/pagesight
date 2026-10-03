import torch
from colpali_engine.utils.processing_utils import BaseVisualRetrieverProcessor

from pagesight.retrieval.maxsim import maxsim, pad

QUERY = torch.tensor([[1.0, 0.0], [0.0, 1.0]])  # two query tokens


def test_maxsim_sums_each_query_tokens_best_patch():
    page_a = torch.tensor([[1.0, 0.0], [0.5, 0.5]])  # q1 best 1.0, q2 best 0.5 -> 1.5
    page_b = torch.tensor([[0.0, 1.0], [0.6, 0.8]])  # q1 best 0.6, q2 best 1.0 -> 1.6
    pages, mask = pad([page_a, page_b])

    assert maxsim(QUERY, pages, mask).tolist() == torch.tensor([1.5, 1.6]).tolist()


def test_maxsim_ignores_padding_patches():
    # Page c has one real patch (-1, 0); padding adds a zero vector that would score 0 for q1.
    page_c = torch.tensor([[-1.0, 0.0]])
    longer = torch.tensor([[1.0, 0.0], [0.0, 1.0]])
    pages, mask = pad([page_c, longer])

    assert maxsim(QUERY, pages, mask)[0].item() == -1.0  # q1: -1, q2: 0


def test_maxsim_matches_colpali_engine_on_random_embeddings():
    torch.manual_seed(0)
    # non-negative, so colpali-engine's unmasked zero padding never wins the max
    query = torch.rand(5, 8)
    page_list = [torch.rand(n, 8) for n in (3, 7, 4)]
    pages, mask = pad(page_list)

    ours = maxsim(query, pages, mask)
    reference = BaseVisualRetrieverProcessor.score_multi_vector(
        [query], page_list, device="cpu"
    )[0]
    assert torch.allclose(ours, reference, atol=1e-5)
