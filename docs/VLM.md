# Small vision-language models for PageSight answers

Checked on 2026-10-04 from public web pages, the Hugging Face (HF) API and source code only (no weights downloaded,
nothing installed or run). Params, licence id, gated flag, bf16 size (sum of `.safetensors` files) and creation date
come from `https://huggingface.co/api/models/<id>?blobs=true`; "card" = the HF page linked in the table; other sources
are listed at the bottom. "Unverified"/"?" = no source confirms it; "est." = our own arithmetic; "—" = not reported.

## Terms

- *VLM*: a model that reads images plus text and writes text. *VRAM*: graphics-card memory. *bf16*: 2 bytes per
  parameter. *NF4*: bitsandbytes' 4-bit format; it replaces linear layers only, so embedding tables stay bf16 ([bnb]).
- *Native*: the model code ships inside `transformers`; *remote code* (`trust_remote_code=True`) runs Python files
  from the model repo instead. *Image tokens*: the vectors a page becomes; more tokens = more detail, VRAM and time.
- *Dynamic resolution*: the page keeps about its own size, so tokens grow with pixels up to a *max-pixels* cap.
  *Tiles*: the page is cut into fixed squares (e.g. 448 px), each worth a fixed number of tokens.
- Scores: *DocVQA* (document scans), *ChartQA* (charts), *InfoVQA* (infographics) in % correct; *OCRBench* (text
  reading) out of 1,000. Test split unless "v" (validation) or "*" (split not stated); vendor-reported unless stated.

## Fit in ~6.9 GB of free VRAM, and table conventions

- 4B models are 8–9.5 GB in bf16, so bf16 fits only up to ~2.5B parameters (≤ ~5 GB, plus page tokens); 4B needs
  NF4 (~3–3.5 GB, est.); 8B-class still takes ~6 GB+ in NF4 (embeddings and output layer stay bf16): too tight (est.).
- "Tokens/A4": est. for a 1654×2339 px page at default settings, from each processor's config and code ([tf-src]);
  US-letter (1700×2200) is similar except InternVL (3,328) and SmolVLM2 (1,377).
- "Native since": first `transformers` release with the model class ([tf-rel]); every native row is in 5.18.0 (the
  installed version). torchvision, used by the default image processors, is already a project dependency.
- Multi-image "yes" is from the card or paper; for Qwen3.5 and Gemma 4, from third-party MuirBench runs ([lfm3]).

## Comparison

| Model (card) | Params | Licence (gated) | bf16 GB | Native since | Extra pip | Tokens/A4 | Multi-image | Doc · Chart · Info · OCRBench | Created | Fits (est.) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| [Qwen/Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) | 2.27B | apache-2.0 (no) | 4.55 | 5.2.0 | — | ~3.8k dynamic | yes | — · — · — · 854 (direct) card | 2026-02-28 | bf16 |
| [Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | 4.66B | apache-2.0 (no) | 9.32 | 5.2.0 | — | ~3.8k dynamic | yes | — · — · — · 850 (thinking) card | 2026-02-27 | NF4 |
| [Qwen/Qwen3-VL-2B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct) | 2.13B | apache-2.0 (no) | 4.26 | 4.57.0 | — | ~3.8k dynamic | yes | 93.3 · 79.1 · 72.4 · 858 [q3vl] | 2025-10-19 | bf16 |
| [Qwen/Qwen3-VL-4B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-4B-Instruct) | 4.44B | apache-2.0 (no) | 8.88 | 4.57.0 | — | ~3.8k dynamic | yes | 95.3 · 84.6 · 80.3 · 881 [q3vl] | 2025-10-11 | NF4 |
| [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | 8.77B | apache-2.0 (no) | 17.53 | 4.57.0 | — | ~3.8k dynamic | yes | 96.1 · 89.6 · 83.1 · 896 [q3vl] | 2025-10-11 | no |
| [Qwen/Qwen2.5-VL-3B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct) | 3.75B | qwen-research (no) | 7.51 | 4.49.0 | qwen-vl-utils (optional) | ~5.0k dynamic | yes | 93.9 · 84.0 · 77.1 · 797 [q25vl] | 2025-01-26 | NF4 |
| [Qwen/Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct) | 8.29B | apache-2.0 (no) | 16.58 | 4.49.0 | qwen-vl-utils (optional) | ~5.0k dynamic | yes | 95.7 · 87.3 · 82.6 · 864 [q25vl] | 2025-01-26 | no |
| [OpenGVLab/InternVL3_5-1B-HF](https://huggingface.co/OpenGVLab/InternVL3_5-1B-HF) | 1.06B | apache-2.0 (no) | 2.12 | 4.52.1 | — | 1,792 tiles | yes | 85.6 · 77.7 · 60.5 · 795 [ivl35] | 2025-08-29 | bf16 |
| [OpenGVLab/InternVL3_5-2B-HF](https://huggingface.co/OpenGVLab/InternVL3_5-2B-HF) | 2.35B | apache-2.0 (no) | 4.70 | 4.52.1 | — | 1,792 tiles | yes | 89.4 · 80.7 · 70.8 · 836 [ivl35] | 2025-08-29 | bf16 |
| [OpenGVLab/InternVL3_5-4B-HF](https://huggingface.co/OpenGVLab/InternVL3_5-4B-HF) | 4.73B | apache-2.0 (no) | 9.47 | 4.52.1 | — | 1,792 tiles | yes | 92.4 · 86.0 · 78.0 · 822 [ivl35] | 2025-08-29 | NF4 |
| [CohereLabs/North-Micro-Vision-Instruct](https://huggingface.co/CohereLabs/North-Micro-Vision-Instruct) | 2.48B | apache-2.0 (no) | 4.97 | 5.16.0 | — | ~3.8k dynamic | yes | 92.1v · 80.8 · 65.2v · 792 card | 2026-08-10 | bf16 |
| [openbmb/MiniCPM-V-4.6](https://huggingface.co/openbmb/MiniCPM-V-4.6) | 1.30B | apache-2.0 (no) | 2.60 | 5.7.0 | — | ~640 slices | yes | 86.4v · — · — · 824 [mcpm46] | 2026-04-13 | bf16 |
| [openbmb/MiniCPM-V-4](https://huggingface.co/openbmb/MiniCPM-V-4) | 4.06B | apache-2.0 (no) | 8.12 | remote code | unverified | unverified | yes | 92.9* · 84.4* · — · 894 card | 2025-07-12 | NF4 |
| [openbmb/MiniCPM-V-4_5](https://huggingface.co/openbmb/MiniCPM-V-4_5) | 8.70B | apache-2.0 (no) | 17.39 | remote code | unverified | unverified | yes | 94.7* (thinking) · 87.4* · — · 890 [mcpm45] | 2025-08-24 | no |
| [HuggingFaceTB/SmolVLM2-2.2B-Instruct](https://huggingface.co/HuggingFaceTB/SmolVLM2-2.2B-Instruct) | 2.25B | apache-2.0 (no) | 8.99 (fp32 files) | 4.50.0 | num2words | ~1.05k tiles | yes | 80.0v · 68.8 · — · 729 card | 2025-02-08 | bf16 |
| [google/gemma-3-4b-it](https://huggingface.co/google/gemma-3-4b-it) | 4.30B | gemma (yes, manual) | 8.60 | 4.50.0 | — | 256 (one 896 px view) | ? | 75.8 · 68.8 · 50.0 · — [g3] | 2025-02-20 | NF4 |
| [google/gemma-4-E2B-it](https://huggingface.co/google/gemma-4-E2B-it) | 5.12B | apache-2.0 (no) | 10.25 | 5.5.0 | — | ~266 (budget 280) | yes | — · — · — · — | 2026-03-02 | no |
| [microsoft/Phi-4-multimodal-instruct](https://huggingface.co/microsoft/Phi-4-multimodal-instruct) | 5.57B | mit (no) | 12.81 | remote code | flash_attn, peft, backoff, soundfile, scipy | unverified | yes | 93.2* · 81.4* · 72.7* · 844 card | 2025-02-24 | NF4 |
| [ibm-granite/granite-vision-3.3-2b](https://huggingface.co/ibm-granite/granite-vision-3.3-2b) | 2.98B | apache-2.0 (no) | 5.95 | card: ≥ 4.49 | — | ~5.4k tiles | ? | 91* · 87* · 68* · 790 card | 2025-06-03 | NF4 |
| [ibm-granite/granite-vision-4.1-4b](https://huggingface.co/ibm-granite/granite-vision-4.1-4b) | 4.00B | apache-2.0 (no) | 7.99 | 5.8.0 | peft ≥ 0.19.1 | unverified | ? | — (extraction tasks only) | 2026-04-16 | NF4 |
| [LiquidAI/LFM2.5-VL-1.6B](https://huggingface.co/LiquidAI/LFM2.5-VL-1.6B) | 1.60B | other: lfm1.0 (no) | 3.19 | 4.57.0 | — | ~1.8k tiles | yes | — · — · 62.7v · — card | 2026-01-05 | bf16 |
| [LiquidAI/LFM2.5-VL-3B](https://huggingface.co/LiquidAI/LFM2.5-VL-3B) | 3.12B | other: lfm1.0 (no) | 6.25 | 4.57.0 | — | ~1.8k tiles | yes | — · 81.3* · — · — card | 2026-08-11 | NF4 |
| [mistralai/Ministral-3-3B-Instruct-2512](https://huggingface.co/mistralai/Ministral-3-3B-Instruct-2512) | 3.85B | apache-2.0 (no) | 7.70 (BF16 repo) | 5.0.0 | mistral-common ≥ 1.8.6 | ~2.2k dynamic | ? | — · — · — · — | 2025-10-31 | NF4 |

## Notes per model

- **Qwen3.5** (cards): trained on text and images together; only 6 of the 2B's 24 layers use full attention, the rest
  *linear attention* (memory that does not grow with length), and transformers ships plain-PyTorch versions ([tf-src]).
  The 2B answers directly by default; the 4B *thinks* (writes reasoning first) unless `enable_thinking=False`.
- **Qwen-style pixels** (Qwen3-VL, Qwen3.5, North): one token per 32×32 px; the default cap (16.8 MP) keeps a
  whole page (~3.8k tokens); `size["longest_edge"]` in `preprocessor_config.json` is the cap (1,310,720 px → ~1.26k
  tokens, est.). Qwen2.5-VL: one token per 28×28 px; its 3B licence is non-commercial only ([qr-lic]), fine for us.
- **InternVL3.5-HF** (card): native, the repo has no Python files (the card's snippet still passes `trust_remote_code`);
  ≤ 12 tiles of 448 px + a thumbnail, 256 tokens each: an A4 page is 2×3 tiles, read at 896×1344 px ([tf-src]).
- **North Micro Vision** (card): 2B language model + 400M vision encoder; multimodal contexts over 8K tokens "have not
  been validated", so 3 full pages (~11k tokens) need a lower cap. The card pins transformers 5.16.0.
- **MiniCPM-V 4.6** (card, [mcpm46]): Qwen3.5-0.8B + 400M encoder; ≤ 9 slices of 448 px compressed 16× (est. ~640
  tokens); `downsample_mode="4x"` keeps 4× more (DocVQA-v 89.4, OCRBench 838). MiniCPM-V 4 and 4.5 need remote code.
- **SmolVLM2**: float32 files (~4.5 GB as bf16, est.); its processor will not start without `num2words` ([tf-src]).
- **Gemma**: Gemma 3 4B is gated (HF account + accepting terms), against the project's no-account rule ([g3] for its
  scores). Gemma 4 (card): per-layer embedding tables make the E2B 5.1B parameters (E4B: 8.00B, 15.99 GB) and NF4 does
  not shrink them ([bnb]): no fit without CPU offload (est.). Default image budget 280 tokens (A4 read at 672×912 px,
  est.; max 1,120); third-party ChartQA 42.2–43.5, DocVQA-v 73.2–74.5 ([north], [lfm3], [mcpm46]).
- **Phi-4-multimodal** (card): remote code pinned to transformers 4.48.2 (a native class since 4.51.0 is untested).
- **Granite Vision** (cards): 3.3-2b (released 2025-06-11) tiles 384 px squares on a fixed grid list (est. ~5.4k
  tokens), scores on a 0–1 scale; 4.1-4b (released 2026-04-29) is built for chart, table and key-value extraction.
- **LFM2.5-VL**: LFM Open License v1.0 limits commercial use to companies under US$10M yearly revenue ([lfm-lic]);
  512 px tiles (2 to 10) + a thumbnail, ≤ 256 tokens each. **Ministral 3** (card): main repo FP8; BF16 repo 7.70 GB.
- Left out: over 8B parameters (Qwen3.5-9B, GLM-4.6V-Flash, apple/LensVLM-9B); 8B-class in NF4 (Qwen3-VL-8B,
  Qwen2.5-VL-7B, InternVL3.5-8B-HF, MiniCPM-V 4.5, MiMo-VL-7B-RL-2508); remote code or not in transformers 5.18.0
  (Molmo2-4B, Youtu-VL-4B, Mage-VL, Qianfan-VL-3B, MiniCPM-V 4/4.5, Phi-4-multimodal).

## Third-party re-runs (same settings for every model)

| Cohere's VLMEvalKit run ([north]) | Qwen3.5-2B | North | Ministral-3-3B | LFM2.5-VL-1.6B | Qwen3-VL-2B | SmolVLM2 | Gemma-4-E2B |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ChartQA test / DocVQA val | 77.5 / 92.6 | 80.8 / 92.1 | 79.1 / 89.6 | 73.9 / 87.7 | 69.3 / 82.5 | 68.2 / 79.9 | 42.2 / 73.2 |
| InfoVQA val / OCRBench | 73.1 / 861 | 65.2 / 792 | 58.9 / 735 | 62.7 / 802 | 62.2 / 751 | 38.3 / 727 | 38.0 / 719 |

Liquid AI's run ([lfm3]), ChartQA: InternVL3.5-2B 81.8, InternVL3.5-4B 86.5, Qwen3.5-2B 78.3, Qwen3.5-4B 84.2. Vendor
and re-run numbers differ (Qwen3-VL-2B DocVQA: 93.3 test in [q3vl], 82.5 val above), so we must measure ourselves.

## Shortlist for measurement

1. `Qwen/Qwen3.5-2B`, bf16 (4.55 GB): best 2B-class model in Cohere's re-run (DocVQA-v 92.6, InfoVQA-v 73.1,
   OCRBench 861); native, apache-2.0, answers directly by default, small cache even for 3 full pages.
2. `Qwen/Qwen3.5-4B`, NF4 (9.32 GB download, ~3.5 GB loaded, est.): the largest model that still fits; a clear step up
   in Liquid's re-run (ChartQA 84.2 vs 78.3 for the 2B); same processor and prompts, so it isolates model size.
3. `OpenGVLab/InternVL3_5-2B-HF`, bf16 (4.70 GB): a second family as a control; fewer tokens on A4 pages (1,792 vs
   ~3.8k), strong on charts (ChartQA 80.7 reported, 81.8 re-run); native, apache-2.0.

Total download: 18,564,839,912 bytes = 18.56 GB (17.29 GiB). NF4 needs `bitsandbytes` (not installed; 0.50.2 has a
Windows x64 wheel, [bnb-pypi]). Back-ups: Qwen3-VL-4B-Instruct (NF4, plain attention) and North-Micro-Vision-Instruct.

[bnb]: https://huggingface.co/docs/transformers/main/en/quantization/bitsandbytes
[bnb-pypi]: https://pypi.org/project/bitsandbytes/
[tf-src]: https://github.com/huggingface/transformers/tree/v5.18.0/src/transformers/models
[tf-rel]: https://github.com/huggingface/transformers/releases
[q3vl]: https://arxiv.org/pdf/2511.21631
[q25vl]: https://arxiv.org/html/2502.13923
[ivl35]: https://arxiv.org/html/2508.18265
[mcpm45]: https://arxiv.org/html/2509.18154
[g3]: https://arxiv.org/html/2503.19786
[mcpm46]: https://raw.githubusercontent.com/openbmb/MiniCPM-V/main/assets/minicpmv4.6/instruct.png
[north]: https://huggingface.co/CohereLabs/North-Micro-Vision-Instruct
[lfm3]: https://huggingface.co/LiquidAI/LFM2.5-VL-3B
[qr-lic]: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/blob/main/LICENSE
[lfm-lic]: https://huggingface.co/LiquidAI/LFM2.5-VL-1.6B/blob/main/LICENSE
