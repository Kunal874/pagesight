"""Answer model (D-032): Qwen3.5-4B in 4-bit, loaded on demand and unloaded to free VRAM (Task 6.1).
Also serves as the text-only judge (D-034)."""

import gc
from pathlib import Path

import torch
from PIL import Image

MODEL = "Qwen/Qwen3.5-4B"
REVISION = "851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a"  # pinned (D-032)
MAX_PIXELS = 1_600_000  # per page, the setting measured in results/vlm_probe.md
MAX_NEW_TOKENS = 128
YES_WORDS, NO_WORDS = ("YES", "Yes", "yes"), ("NO", "No", "no")


def yes_probability(
    logits: torch.Tensor, yes_ids: list[int], no_ids: list[int]
) -> float:
    """P(YES) when the model must choose between the YES and NO tokens (spellings pooled)."""
    return torch.sigmoid(
        logits[yes_ids].logsumexp(0) - logits[no_ids].logsumexp(0)
    ).item()


def load_image(path: Path, max_pixels: int = MAX_PIXELS) -> Image.Image:
    """The page scaled down (never up) to at most max_pixels, keeping its aspect ratio."""
    img = Image.open(path).convert("RGB")
    scale = min(1.0, (max_pixels / (img.width * img.height)) ** 0.5)
    # int() rounds down, so the area never exceeds the budget
    size = (int(img.width * scale), int(img.height * scale))
    return img if size == img.size else img.resize(size, Image.LANCZOS)


class AnswerModel:
    def __init__(self, quantize: bool = True):
        # 4-bit is what fits the 8 GB laptop and what was evaluated (D-032); the 48 GB demo GPU runs
        # bf16, because bitsandbytes quantizes while loading and ZeroGPU loads without a real GPU
        self.quantize = quantize
        self.model = self.processor = None

    def load(self) -> None:
        # heavy imports, only when the model is really needed
        from transformers import (
            AutoModelForImageTextToText,
            AutoProcessor,
            BitsAndBytesConfig,
        )

        quant = (
            BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            if self.quantize
            else None
        )
        self.model = AutoModelForImageTextToText.from_pretrained(
            MODEL,
            revision=REVISION,
            dtype=torch.bfloat16,
            device_map="cuda",
            quantization_config=quant,
        ).eval()
        self.processor = AutoProcessor.from_pretrained(MODEL, revision=REVISION)
        tok = self.processor.tokenizer
        # first token of each spelling; load() checks below that each is a single token
        self.yes_ids, self.no_ids = (
            [tok.encode(w, add_special_tokens=False)[0] for w in words]
            for words in (YES_WORDS, NO_WORDS)
        )
        if any(
            len(tok.encode(w, add_special_tokens=False)) != 1
            for w in YES_WORDS + NO_WORDS
        ):
            raise ValueError(
                "a YES/NO spelling is not a single token for this tokenizer"
            )

    def unload(self) -> None:
        self.model = self.processor = None
        gc.collect()
        torch.cuda.empty_cache()

    def inputs(self, messages: list[dict]):
        if self.model is None:
            self.load()
        return self.processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            enable_thinking=False,  # Qwen3.5-4B would otherwise reason before answering
        ).to(self.model.device)

    @torch.inference_mode()
    def generate(
        self, messages: list[dict], max_new_tokens: int = MAX_NEW_TOKENS
    ) -> str:
        inputs = self.inputs(messages)
        out = self.model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False
        )
        new = out[0, inputs["input_ids"].shape[1] :]
        return self.processor.decode(new, skip_special_tokens=True)

    @torch.inference_mode()
    def p_yes(self, messages: list[dict]) -> float:
        """The gate (D-036): the first-token probability of YES against NO."""
        inputs = self.inputs(messages)  # first: it loads the model on demand
        out = self.model.generate(
            **inputs,
            max_new_tokens=1,
            do_sample=False,
            output_logits=True,
            return_dict_in_generate=True,
        )
        return yes_probability(out.logits[0][0].float(), self.yes_ids, self.no_ids)
