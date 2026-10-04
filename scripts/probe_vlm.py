"""Group 6 evidence: VRAM and seconds per answer for one candidate VLM on 3 dev sample pages (an hr
chart, a finance_en table and a text-only page, each with its question), plus one prompt with all
3 pages. Every page is resized to the same pixel budget, so models are compared on equal input.

Usage: uv run python scripts/probe_vlm.py <hf-model-id> [--four-bit] [--max-pixels N]
       -> appends a section to results/vlm_probe.md
"""

import argparse
import time

import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

from pagesight.data.split import load_split
from pagesight.data.vidore import Page, Query, load_pages, load_queries
from pagesight.eval.runner import RESULTS, git_state

ABSTAIN = "If the pages do not answer the question, reply exactly NOT_FOUND.\n"
PROMPT = (
    "Answer the question using only the page images. Cite the page you used as [p:<page id>]. "
    "{abstain}Pages, in order: {ids}\nQuestion: {question}"
)
MAX_NEW_TOKENS = 128


def samples() -> list[tuple[Query, Page]]:
    """First dev query by id of each kind that is specific: a fully relevant (grade 2) page and
    at most 3 gold pages. Returns it with that grade-2 page."""
    dev = set(load_split()["dev"])
    picks = []
    for subset, kind in (("hr", "Chart"), ("finance_en", "Table"), ("hr", "Text")):
        pages = {p.id: p for p in load_pages(subset)}
        queries = sorted(load_queries(subset), key=lambda q: q.id)
        q = next(
            q
            for q in queries
            if q.id in dev
            and 2 in q.gold.values()
            and len(q.gold) <= 3
            and (
                q.content_types == ["Text"]
                if kind == "Text"
                else kind in q.content_types
            )
        )
        picks.append((q, pages[max(q.gold, key=q.gold.get)]))
    return picks


def load_image(page: Page, max_pixels: int) -> Image.Image:
    img = Image.open(page.image).convert("RGB")
    scale = min(1.0, (max_pixels / (img.width * img.height)) ** 0.5)
    return img.resize(
        (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
    )


@torch.inference_mode()
def answer(
    model, processor, question: str, pages: list[Page], max_pixels: int, abstain: str
) -> dict:
    content = [{"type": "image", "image": load_image(p, max_pixels)} for p in pages]
    ids = ", ".join(p.id for p in pages)
    content.append(
        {
            "type": "text",
            "text": PROMPT.format(abstain=abstain, ids=ids, question=question),
        }
    )
    inputs = processor.apply_chat_template(
        [{"role": "user", "content": content}],
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
        # Qwen3.5-4B writes its reasoning first unless told not to; other templates ignore it
        enable_thinking=False,
    ).to(model.device)
    torch.cuda.reset_peak_memory_stats()
    start = time.perf_counter()
    out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    seconds = time.perf_counter() - start
    new = out[0, inputs["input_ids"].shape[1] :]
    return {
        "input tokens": inputs["input_ids"].shape[1],
        "new tokens": len(new),
        "seconds": seconds,
        "peak VRAM GB": torch.cuda.max_memory_allocated() / 2**30,
        "answer": processor.decode(new, skip_special_tokens=True).strip(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("--four-bit", action="store_true")
    parser.add_argument("--max-pixels", type=int, default=1_600_000)
    # without the NOT_FOUND sentence: can the model read the page when it has no way out?
    parser.add_argument("--no-abstain", action="store_true")
    args = parser.parse_args()

    quant = (
        BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        if args.four_bit
        else None
    )
    start = time.perf_counter()
    model = AutoModelForImageTextToText.from_pretrained(
        args.model, dtype=torch.bfloat16, device_map="cuda", quantization_config=quant
    ).eval()
    processor = AutoProcessor.from_pretrained(args.model)
    load_s = time.perf_counter() - start
    weights_gb = torch.cuda.memory_allocated() / 2**30

    abstain = "" if args.no_abstain else ABSTAIN
    picks = samples()
    rows = [(q.id, q, [page]) for q, page in picks]
    rows.append(("3 pages", picks[0][0], [page for _, page in picks]))
    git = git_state()
    lines = [
        "",
        f"## {args.model} ({'4-bit NF4' if args.four_bit else 'bf16'})"
        + (", prompt without the NOT_FOUND sentence" if args.no_abstain else ""),
        "",
        (
            f"`scripts/probe_vlm.py` at {git['commit']}{'+dirty' if git['dirty'] else ''}; "
            f"revision {getattr(model.config, '_commit_hash', 'unknown')}; max {args.max_pixels:,} "
            f"pixels per page; load {load_s:.0f} s; weights {weights_gb:.2f} GB VRAM; greedy, "
            f"max {MAX_NEW_TOKENS} new tokens."
        ),
        "",
        "| sample | input tokens | new tokens | seconds | peak VRAM GB | answer | reference |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for name, q, pages in rows:
        r = answer(model, processor, q.text, pages, args.max_pixels, abstain)
        reply = r["answer"].replace("|", "/").replace("\n", " ")[:160]
        cells = [
            name,
            r["input tokens"],
            r["new tokens"],
            f"{r['seconds']:.1f}",
            f"{r['peak VRAM GB']:.2f}",
            reply,
            q.answer.replace("|", "/").replace("\n", " ")[:120],
        ]
        lines.append(f"| {' | '.join(map(str, cells))} |")
        print(lines[-1])
    path = RESULTS / "vlm_probe.md"
    if not path.exists():
        path.write_text(
            "# VLM probe\n\nOne section per candidate; peak VRAM is "
            "`torch.cuda.max_memory_allocated` during generation.\n",
            encoding="utf-8",
        )
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
