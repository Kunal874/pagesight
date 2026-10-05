"""Visual retrieval with ColSmol (D-021): each page image -> one vector per patch, each query ->
one vector per token, scored with MaxSim. Page vectors are cached under indexes/ and reused."""

import time
from pathlib import Path

import torch
from PIL import Image

from pagesight.config import ROOT
from pagesight.data.vidore import Page
from pagesight.retrieval.maxsim import maxsim, pad

# LoRA adapter -> (adapter revision, base model, base revision), pinned for reproducibility (D-021)
MODELS = {
    "vidore/colSmol-256M": (
        "c79b633e17e060cc109b11aa2bf92a1517d3bd6f",
        "vidore/ColSmolVLM-Instruct-256M-base",
        "99ca96f1f6b95b3a69e6abef74a2416cb738fed0",
    ),
    "vidore/colSmol-500M": (
        "0aaa9726104ce485884c7b8faa8a58a72d5fdbe7",
        "vidore/ColSmolVLM-Instruct-500M-base",
        "650243e9bf299a5a082841ed2907da8b0b9ce553",
    ),
}
CACHE = ROOT / "indexes" / "colsmol"


def cache_path(model: str, subset: str) -> Path:
    return CACHE / model.replace("/", "__") / f"{subset}.pt"


def load_model(name: str):
    from colpali_engine.models import ColIdefics3, ColIdefics3Processor
    from huggingface_hub import snapshot_download

    adapter_revision, base, base_revision = MODELS[name]
    # from_pretrained(adapter, revision=...) reuses that revision for the base repo and fails,
    # so each repo is fetched at its own pinned revision and loaded from its local snapshot.
    adapter_dir = snapshot_download(name, revision=adapter_revision)
    base_dir = snapshot_download(base, revision=base_revision)
    model = ColIdefics3.from_pretrained(
        base_dir, dtype=torch.bfloat16, device_map="cuda"
    )
    model.load_adapter(adapter_dir)
    return model.eval(), ColIdefics3Processor.from_pretrained(adapter_dir)


@torch.inference_mode()
def embed_pages(
    model, processor, pages: list[Page], batch_size: int
) -> list[torch.Tensor]:
    out = []
    for i in range(0, len(pages), batch_size):
        images = [Image.open(p.image).convert("RGB") for p in pages[i : i + batch_size]]
        batch = processor.process_images(images).to(model.device)
        for e in model(**batch):
            # drop rows the model zeroed (padding)
            out.append(e[e.norm(dim=-1) > 0].cpu())
    return out


@torch.inference_mode()
def embed_query(model, processor, query: str) -> torch.Tensor:
    e = model(**processor.process_queries(texts=[query]).to(model.device))[0]
    return e[e.norm(dim=-1) > 0]


def tile_grid(
    input_ids: list[int],
    scores: torch.Tensor,
    tags: dict[int, tuple[int, int]],
    seq_len: int,
) -> torch.Tensor:
    """Per-token scores laid out on the page (D-044). Idefics3 cuts the page into tiles and emits
    each tile's seq_len image tokens, row by row, right after its <row_i_col_j> tag; the downscaled
    global tile at the end has no tag and is left out."""
    side = round(seq_len**0.5)
    found = [(p, tags[t]) for p, t in enumerate(input_ids) if t in tags]
    rows, cols = max(i for _, (i, _) in found), max(j for _, (_, j) in found)
    grid = torch.zeros(rows * side, cols * side)
    for p, (i, j) in found:
        block = scores[p + 1 : p + 1 + seq_len].reshape(side, side)
        grid[(i - 1) * side : i * side, (j - 1) * side : j * side] = block
    return grid


@torch.inference_mode()
def heatmap(model, processor, image: Image.Image, query: str) -> torch.Tensor:
    """How well each page region matches the question's best-matching word: for every image token,
    the highest similarity to any word token of the query (the 10 padding tokens are left out)."""
    batch = processor.process_images([image]).to(model.device)
    page = model(**batch)[0].float()
    words = len(processor.tokenizer(query, add_special_tokens=False).input_ids)
    q = embed_query(model, processor, query).float()[:words]
    scores = (q @ page.T).max(dim=0).values.cpu()
    tok = processor.tokenizer
    tags = {
        tok.convert_tokens_to_ids(f"<row_{i}_col_{j}>"): (i, j)
        for i in range(1, 7)
        for j in range(1, 7)
    }
    return tile_grid(
        batch["input_ids"][0].tolist(), scores, tags, processor.image_seq_len
    )


def overlay(image: Image.Image, grid: torch.Tensor) -> Image.Image:
    """The page with the heatmap in red: transparent where the match is weakest."""
    g = grid - grid.min()
    g = (255 * g / g.max().clamp(min=1e-6)).to(torch.uint8).numpy()
    alpha = Image.fromarray(g).resize(image.size, Image.BILINEAR)
    red = Image.new("RGB", image.size, (230, 30, 30))
    return Image.composite(red, image.convert("RGB"), alpha.point(lambda a: a * 0.6))


class ColSmolRetriever:
    def __init__(self, pages: list[Page], model: str, batch_size: int):
        self.ids = [p.id for p in pages]
        self.model, self.processor = load_model(model)
        path = cache_path(model, pages[0].id.rsplit("-", 1)[0])
        cache = torch.load(path, weights_only=True) if path.exists() else {}
        missing = [p for p in pages if p.id not in cache]
        self.stats = {"pages_embedded": len(missing)}
        if missing:
            start = time.perf_counter()
            vectors = embed_pages(self.model, self.processor, missing, batch_size)
            seconds = time.perf_counter() - start
            self.stats["embed_seconds_per_page"] = seconds / len(missing)
            cache.update(zip((p.id for p in missing), vectors, strict=True))
            path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(cache, path)
        # float32 for exact scores; ~1.7 GB for the largest subset (finance_en)
        self.pages, self.mask = pad(
            [cache[i].to("cuda", torch.float32) for i in self.ids]
        )

    def search(self, query: str, k: int) -> list[str]:
        q = embed_query(self.model, self.processor, query).float()
        scores = maxsim(q, self.pages, self.mask)
        return [self.ids[i] for i in scores.topk(k).indices.tolist()]
