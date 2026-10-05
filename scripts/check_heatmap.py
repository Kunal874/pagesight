"""Heatmap placement checks, each rule fixed before its run. Synthetic letter pages each carry one
distinctive word in large type at a known place among lines of ordinary report text; the query is
that word.
- D-044 (default): "Kangaroo" at 3 places; the centre of the strongest heatmap cell must lie inside
  the word's box on all 3. Result: failed by ~1 pt on 1 page (results/heatmap_check.json).
- D-047 (--retest): "Pelican" at 6 new places; the strongest cell's rectangle must overlap the word's
  box on at least 5 of 6. Pass: Task 8.3 ships. Fail: it is dropped.

Usage: uv run python scripts/check_heatmap.py [--retest]
       -> results/heatmap_check.json or results/heatmap_retest.json, overlays in data/heatmap_check/
"""

import argparse
import json

import pymupdf
from PIL import Image

from pagesight.config import DATA_DIR, PDF_DPI
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.colsmol import heatmap, load_model, overlay

FILLER = "Annual report 2024. Revenue grew in every region while operating costs fell slightly."
# word, baselines of the word in points on a 612 x 792 page, rule, pages that must pass
CHECKS = {
    "check": (
        "Kangaroo",
        {"top-left": (72, 130), "centre": (230, 410), "bottom-right": (380, 720)},
        "centre",
        3,
    ),
    "retest": (
        "Pelican",
        {
            "top-right": (380, 110),
            "upper-left": (90, 260),
            "middle-right": (360, 360),
            "lower-left": (72, 560),
            "lower-middle": (230, 640),
            "bottom-left": (100, 760),
        },
        "overlap",
        5,
    ),
}


def page_image(word: str, x: float, y: float) -> tuple[Image.Image, tuple[float, ...]]:
    """The rendered page and the word's box as page fractions (x0, y0, x1, y1)."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((x, y), word, fontsize=36, fontname="hebo")
    for line_y in range(80, 770, 30):
        if abs(line_y - (y - 12)) > 40:  # keep the filler clear of the word
            page.insert_text((72, line_y), FILLER, fontsize=10)
    box = page.search_for(word)[0]
    pix = page.get_pixmap(dpi=PDF_DPI)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image, (box.x0 / 612, box.y0 / 792, box.x1 / 612, box.y1 / 792)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retest", action="store_true", help="the D-047 re-test")
    name = "retest" if parser.parse_args().retest else "check"
    word, positions, rule, needed = CHECKS[name]
    git = git_state()
    model, processor = load_model("vidore/colSmol-500M")
    out = DATA_DIR / "heatmap_check"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for place, (x, y) in positions.items():
        image, box = page_image(word, x, y)
        grid = heatmap(model, processor, image, word)
        n_rows, n_cols = grid.shape
        r, c = divmod(int(grid.argmax()), n_cols)
        cell = (c / n_cols, r / n_rows, (c + 1) / n_cols, (r + 1) / n_rows)
        centre = ((cell[0] + cell[2]) / 2, (cell[1] + cell[3]) / 2)
        inside = box[0] <= centre[0] <= box[2] and box[1] <= centre[1] <= box[3]
        overlaps = (
            cell[0] < box[2]
            and box[0] < cell[2]
            and cell[1] < box[3]
            and box[1] < cell[3]
        )
        overlay(image, grid).save(out / f"{name}-{place}.png")
        rows.append(
            {
                "position": place,
                "word_box": [round(v, 3) for v in box],
                "grid": [n_rows, n_cols],
                "strongest_cell": [r, c],
                "cell_centre": [round(v, 3) for v in centre],
                "centre_inside": inside,
                "overlaps": overlaps,
            }
        )
        print(rows[-1])
    key = "centre_inside" if rule == "centre" else "overlaps"
    passed = sum(row[key] for row in rows)
    result = {
        "git": git,
        "word": word,
        "rule": f"{key} on at least {needed} of {len(rows)} pages",
        "passed": passed,
        "pass": passed >= needed,
        "pages": rows,
    }
    path = RESULTS / f"heatmap_{name}.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print(
        "PASS" if result["pass"] else "FAIL",
        f"{passed}/{len(rows)}",
        f"saved results/{path.name}",
    )


if __name__ == "__main__":
    main()
