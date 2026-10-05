"""D-044 check, fixed before the heatmaps were built: are they placed right? Three synthetic letter
pages each carry one distinctive word in large type at a known place (top-left, centre, bottom-right)
among lines of ordinary report text. For a query of that word, the centre of the strongest heatmap
cell must lie inside the word's box on all three pages. Pass: Task 8.3 ships. Fail: it is dropped.

Usage: uv run python scripts/check_heatmap.py
       -> results/heatmap_check.json, overlays for a visual check in data/heatmap_check/
"""

import json

import pymupdf
from PIL import Image

from pagesight.config import DATA_DIR, PDF_DPI
from pagesight.eval.runner import RESULTS, git_state
from pagesight.retrieval.colsmol import heatmap, load_model, overlay

WORD = "Kangaroo"
FILLER = "Annual report 2024. Revenue grew in every region while operating costs fell slightly."
# baseline of the word, in points on a 612 x 792 page
POSITIONS = {"top-left": (72, 130), "centre": (230, 410), "bottom-right": (380, 720)}


def page_image(x: float, y: float) -> tuple[Image.Image, tuple[float, ...]]:
    """The rendered page and the word's box as page fractions (x0, y0, x1, y1)."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text((x, y), WORD, fontsize=36, fontname="hebo")
    for line_y in range(80, 770, 30):
        if abs(line_y - (y - 12)) > 40:  # keep the filler clear of the word
            page.insert_text((72, line_y), FILLER, fontsize=10)
    box = page.search_for(WORD)[0]
    pix = page.get_pixmap(dpi=PDF_DPI)
    image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    return image, (box.x0 / 612, box.y0 / 792, box.x1 / 612, box.y1 / 792)


def main() -> None:
    git = git_state()
    model, processor = load_model("vidore/colSmol-500M")
    out = DATA_DIR / "heatmap_check"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (x, y) in POSITIONS.items():
        image, box = page_image(x, y)
        grid = heatmap(model, processor, image, WORD)
        r, c = divmod(int(grid.argmax()), grid.shape[1])
        centre = ((c + 0.5) / grid.shape[1], (r + 0.5) / grid.shape[0])
        inside = box[0] <= centre[0] <= box[2] and box[1] <= centre[1] <= box[3]
        overlay(image, grid).save(out / f"{name}.png")
        rows.append(
            {
                "position": name,
                "word_box": [round(v, 3) for v in box],
                "grid": list(grid.shape),
                "strongest_cell": [r, c],
                "cell_centre": [round(v, 3) for v in centre],
                "inside": inside,
            }
        )
        print(rows[-1])
    result = {
        "git": git,
        "word": WORD,
        "pages": rows,
        "pass": all(r["inside"] for r in rows),
    }
    path = RESULTS / "heatmap_check.json"
    path.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    print("PASS" if result["pass"] else "FAIL", f"saved results/{path.name}")


if __name__ == "__main__":
    main()
