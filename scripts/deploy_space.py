"""Task 9.3 (D-048, D-049): assemble the demo Space and, only with --push, publish it.

Default (dry run): builds data/space_bundle/ — exactly what the Space repo will hold — and lists it.
--push <hf-user>: needs Kunal's OK and HF_TOKEN (a write token, set as an environment variable, never
committed or typed into a file). Publishes:
  1. dataset repo <user>/pagesight-demo-index <- data/demo/ (build it with scripts/build_demo_index.py)
  2. Space <user>/pagesight (Gradio, ZeroGPU) <- the bundle, with PAGESIGHT_INDEX_REPO pointing at 1.

Usage: uv run python scripts/deploy_space.py [--push <hf-user>]
"""

import argparse
import os
import shutil

from pagesight.config import DATA_DIR, ROOT

BUNDLE = DATA_DIR / "space_bundle"
DEMO = DATA_DIR / "demo"


def bundle() -> None:
    shutil.rmtree(BUNDLE, ignore_errors=True)  # built only by this script
    BUNDLE.mkdir(parents=True)
    for name in ("app.py", "README.md", "requirements.txt"):
        shutil.copy2(ROOT / "space" / name, BUNDLE / name)
    shutil.copy2(ROOT / "LICENSE", BUNDLE / "LICENSE")
    shutil.copytree(
        ROOT / "src" / "pagesight",
        BUNDLE / "src" / "pagesight",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (BUNDLE / "configs").mkdir()
    shutil.copy2(ROOT / "configs" / "split.json", BUNDLE / "configs" / "split.json")
    (BUNDLE / "results").mkdir()
    for report in (ROOT / "results").glob("*.md"):  # the Results tab
        shutil.copy2(report, BUNDLE / "results" / report.name)
    files = sorted(p for p in BUNDLE.rglob("*") if p.is_file())
    size = sum(p.stat().st_size for p in files)
    print(f"bundle: {len(files)} files, {size / 2**20:.1f} MB in {BUNDLE}")
    for p in files:
        print("  ", p.relative_to(BUNDLE).as_posix())


def push(user: str) -> None:
    from huggingface_hub import HfApi

    if not (DEMO / "hr" / "vectors.pt").is_file():
        raise SystemExit("data/demo is missing: run scripts/build_demo_index.py first")
    api = HfApi(token=os.environ["HF_TOKEN"])
    index, space = f"{user}/pagesight-demo-index", f"{user}/pagesight"
    api.create_repo(index, repo_type="dataset", exist_ok=True)
    api.upload_folder(folder_path=DEMO, repo_id=index, repo_type="dataset")
    api.create_repo(
        space,
        repo_type="space",
        space_sdk="gradio",
        space_hardware="zero-a10g",  # the ZeroGPU hardware id
        exist_ok=True,
    )
    api.add_space_variable(space, "PAGESIGHT_INDEX_REPO", index)
    api.upload_folder(folder_path=BUNDLE, repo_id=space, repo_type="space")
    print(
        f"https://huggingface.co/datasets/{index}\nhttps://huggingface.co/spaces/{space}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", metavar="HF_USER")
    args = parser.parse_args()
    bundle()
    if args.push:
        push(args.push)


if __name__ == "__main__":
    main()
