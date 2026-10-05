"""Qdrant index of ColSmol page vectors (D-024): one collection per subset (D-015). Each page is one
point with a "patches" multivector scored by MaxSim, a "pooled" mean vector for a fast first stage
(Group 5) and a payload. Re-runs skip pages already in the collection, so a crashed run resumes.

Usage: docker compose up -d, then uv run python -m pagesight.index.qdrant_store
"""

import argparse
import json
import os
import subprocess
import time

import torch
from qdrant_client import QdrantClient, models
from tqdm import tqdm

from pagesight.config import ROOT, SUBSETS
from pagesight.data.vidore import Page, load_pages
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.colsmol import cache_path


def connect() -> QdrantClient:
    # gRPC has no message-size cap (REST bodies stop at 32 MB; a finance page is ~0.6 MB of floats)
    # QDRANT_HOST: the compose service name when the app runs in Docker (Task 9.1)
    host = os.environ.get("QDRANT_HOST", "127.0.0.1")
    return QdrantClient(host=host, grpc_port=6334, prefer_grpc=True, timeout=300)


def create_collection(client: QdrantClient, name: str, binary: bool) -> None:
    """Does nothing if the collection exists, so a re-run resumes instead of starting over."""
    if client.collection_exists(name):
        return
    quantization = (
        models.BinaryQuantization(binary=models.BinaryQuantizationConfig())
        if binary
        else None
    )
    client.create_collection(
        name,
        vectors_config={
            # Dot on ColSmol's unit vectors = our brute-force MaxSim; m=0: no HNSW graph,
            # "patches" is only scanned or used to rerank candidates
            "patches": models.VectorParams(
                size=128,
                distance=models.Distance.DOT,
                multivector_config=models.MultiVectorConfig(
                    comparator=models.MultiVectorComparator.MAX_SIM
                ),
                hnsw_config=models.HnswConfigDiff(m=0),
                quantization_config=quantization,
            ),
            "pooled": models.VectorParams(size=128, distance=models.Distance.DOT),
        },
    )


def point_id(page: Page) -> int:
    return int(page.id.rsplit("-", 1)[1])  # corpus id: unique within a subset


def to_point(subset: str, page: Page, patches: torch.Tensor) -> models.PointStruct:
    patches = patches.float()
    return models.PointStruct(
        id=point_id(page),
        vector={"patches": patches.tolist(), "pooled": patches.mean(dim=0).tolist()},
        payload={
            "subset": subset,
            "doc_id": page.doc_id,
            "page_number": page.page_number,
            # relative POSIX path, so the index also works from Linux (Docker, Space); uploads may
            # live outside the repo, then the path is kept as it is
            "image": (
                page.image.relative_to(ROOT)
                if page.image.is_relative_to(ROOT)
                else page.image
            ).as_posix(),
        },
    )


def existing_ids(client: QdrantClient, name: str) -> set[int]:
    ids, offset = set(), None
    while True:
        points, offset = client.scroll(
            name, limit=10_000, offset=offset, with_payload=False
        )
        ids.update(p.id for p in points)
        if offset is None:
            return ids


def index_pages(
    client: QdrantClient,
    subset: str,
    pages: list[Page],
    vectors: dict[str, torch.Tensor],
    batch_size: int,
) -> int:
    """Upserts the pages not yet in the collection; returns how many were added."""
    done = existing_ids(client, subset)
    todo = [p for p in pages if point_id(p) not in done]
    with tqdm(total=len(todo), desc=subset, unit="page") as bar:
        for i in range(0, len(todo), batch_size):
            batch = todo[i : i + batch_size]
            client.upsert(subset, [to_point(subset, p, vectors[p.id]) for p in batch])
            bar.update(len(batch))
    return len(todo)


def wait_until_green(client: QdrantClient, name: str) -> None:
    """Blocks until background optimization (segment merges, quantization) has finished."""
    while (info := client.get_collection(name)).status != models.CollectionStatus.GREEN:
        if info.status == models.CollectionStatus.RED:
            raise RuntimeError(f"{name}: {info.optimizer_status}")
        time.sleep(1)


def allocated_bytes(paths: str) -> int:
    # Measured inside the container: the index is in a named volume, not a Windows folder (D-026).
    cmd = ["docker", "compose", "exec", "-T", "qdrant", "sh", "-c"]
    cmd.append(f"du -scB1 {paths} | tail -1")
    out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True)
    return int(out.stdout.split()[0])


def disk_bytes(name: str) -> dict[str, int]:
    """Bytes allocated on disk, not the apparent size: Qdrant preallocates sparse files (64-page
    probe: 1.03 GB apparent, 68 MB allocated). Read until two readings 5 s apart agree, because
    segments replaced by the optimizer are deleted a few seconds after the collection turns green
    (finance_en: 2.09 GB right after green, 1.83 GB once settled)."""
    root = f"/qdrant/storage/collections/{name}"
    patches = f"{root}/*/segments/*/vector_storage-patches"
    parts = {
        "total": root,
        "patches_float32": f"{patches}/vectors {patches}/offsets",
        "patches_binary": f"{patches}/quantized*",
    }
    previous = None
    while (sizes := {k: allocated_bytes(v) for k, v in parts.items()}) != previous:
        previous = sizes
        time.sleep(5)
    return sizes


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="vidore/colSmol-500M")  # D-023
    parser.add_argument("--subsets", nargs="+", default=list(SUBSETS))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--no-binary", action="store_true")
    args = parser.parse_args(argv)

    client = connect()
    result = {
        "model": args.model,
        "binary": not args.no_binary,
        "batch_size": args.batch_size,
        "qdrant": client.info().version,
        "git": git_state(),
        "subsets": {},
    }
    for subset in args.subsets:
        pages = load_pages(subset)
        vectors = torch.load(cache_path(args.model, subset), weights_only=True)
        create_collection(client, subset, binary=not args.no_binary)
        start = time.perf_counter()
        added = index_pages(client, subset, pages, vectors, args.batch_size)
        uploaded = time.perf_counter()
        wait_until_green(client, subset)
        result["subsets"][subset] = {
            "pages": client.count(subset).count,
            "vectors": sum(len(vectors[p.id]) for p in pages),
            "pages_added": added,  # < pages when this run resumed an earlier one
            "upload_seconds": round(uploaded - start, 1),
            "optimize_seconds": round(time.perf_counter() - uploaded, 1),
            "disk_bytes": disk_bytes(subset),
        }
        print(subset, result["subsets"][subset])
    client.close()
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "qdrant_index.json").write_text(
        json.dumps(result, indent=1) + "\n", encoding="utf-8"
    )
    print("saved results/qdrant_index.json")


if __name__ == "__main__":
    main()
