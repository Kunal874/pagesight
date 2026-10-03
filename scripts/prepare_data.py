"""Download the ViDoRe V3 subsets (D-012) into data/: page images, pages.jsonl, queries.jsonl."""

from pagesight.config import SUBSETS
from pagesight.data.vidore import load_pages, load_queries, prepare_subset

for subset, repo in SUBSETS.items():
    prepare_subset(subset, repo)
    pages, queries = load_pages(subset), load_queries(subset)
    missing = sum(not p.image.exists() for p in pages)
    print(
        f"{subset}: {len(pages)} pages ({missing} image files missing), {len(queries)} English queries"
    )
