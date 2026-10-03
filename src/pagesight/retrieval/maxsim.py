"""Late interaction ("MaxSim", as in ColBERT and ColPali): for each query token, take its
best-matching patch on the page; the page's score is the sum of those maxima."""

import torch


def pad(pages: list[torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    """Stack variable-length page embeddings (p_i, d) into (n, max_p, d) plus a mask (n, max_p)
    that is True for real patches."""
    padded = torch.nn.utils.rnn.pad_sequence(pages, batch_first=True)
    lengths = torch.tensor([len(p) for p in pages], device=padded.device)
    mask = (
        torch.arange(padded.shape[1], device=padded.device)[None, :] < lengths[:, None]
    )
    return padded, mask


def maxsim(
    query: torch.Tensor, pages: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """query (q, d); pages (n, p, d) padded; mask (n, p). Returns one score per page, shape (n,)."""
    sim = torch.einsum("qd,npd->nqp", query, pages)
    # padding must never win the max
    sim = sim.masked_fill(~mask[:, None, :], float("-inf"))
    return sim.max(dim=2).values.sum(dim=1)
