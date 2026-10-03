"""Visual retrieval with ColSmol (D-021): each page image -> one vector per patch, each query ->
one vector per token, scored with MaxSim. Page vectors are cached under indexes/ and reused."""

import time

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


class ColSmolRetriever:
    def __init__(self, pages: list[Page], model: str, batch_size: int):
        self.ids = [p.id for p in pages]
        self.model, self.processor = load_model(model)
        subset = pages[0].id.rsplit("-", 1)[0]
        path = CACHE / model.replace("/", "__") / f"{subset}.pt"
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
