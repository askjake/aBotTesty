#!/usr/bin/env python3
"""aBotTesty Phase 2 VLM shadow inference server.

Runs on the 2x3090 box. It loads Qwen3-VL + the trained LoRA adapter and
answers perception/policy/verifier prompts. It never presses remote buttons.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import time
from typing import Any, Dict, List

import torch
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor, BitsAndBytesConfig

try:
    from qwen_vl_utils import process_vision_info
except Exception:
    process_vision_info = None

APP = FastAPI(title="aBotTesty VLM Shadow Server", version="v38-phase2")

MODEL = None
PROCESSOR = None
BASE_MODEL = ""
ADAPTER_PATH = ""
START_TS = time.time()


PROMPTS = {
    "perception": (
        "Analyze this DISH/STB screen. Return ONLY compact JSON with keys: "
        "screen_type, focused_element, selectable_options, risk_flags, confidence."
    ),
    "policy": (
        "You are shadow-observing a DISH/STB UI. Do not execute anything. "
        "Given the current screen and goal, recommend the next SAFE remote action. "
        "Return ONLY compact JSON with keys: action_sequence, expected_result, risk, confidence."
    ),
    "verify": (
        "Compare the before and after TV screens for the requested remote action. "
        "Return ONLY compact JSON with keys: success, evidence, correction, confidence."
    ),
}


def _load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def _jsonish(text: str) -> Any:
    text = (text or "").strip()
    if "```" in text:
        text = text.replace("```json", "```")
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        candidate = text[start : end + 1]
        try:
            return json.loads(candidate)
        except Exception:
            pass
    return {"raw_text": text}


def load_model(base_model: str, adapter_path: str) -> None:
    global MODEL, PROCESSOR, BASE_MODEL, ADAPTER_PATH

    BASE_MODEL = base_model
    ADAPTER_PATH = adapter_path

    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
    )

    PROCESSOR = AutoProcessor.from_pretrained(base_model, trust_remote_code=True)
    base = AutoModelForImageTextToText.from_pretrained(
        base_model,
        trust_remote_code=True,
        quantization_config=quant_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    )
    MODEL = PeftModel.from_pretrained(base, adapter_path)
    MODEL.eval()


def infer(images: List[Image.Image], prompt: str, max_new_tokens: int = 256) -> Dict[str, Any]:
    if MODEL is None or PROCESSOR is None:
        return {"ok": False, "error": "model not loaded"}

    content: List[Dict[str, Any]] = []
    for img in images:
        content.append({"type": "image", "image": img})
    content.append({"type": "text", "text": prompt})

    messages = [{"role": "user", "content": content}]

    if hasattr(PROCESSOR, "apply_chat_template") and process_vision_info is not None:
        text = PROCESSOR.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = PROCESSOR(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
    else:
        image_token_text = "\n".join(["<image>"] * len(images))
        text = f"{image_token_text}\n{prompt}"
        inputs = PROCESSOR(text=[text], images=images, padding=True, return_tensors="pt")

    # Put tensors on the first model device.
    first_param = next(MODEL.parameters())
    inputs = {k: (v.to(first_param.device) if hasattr(v, "to") else v) for k, v in inputs.items()}

    t0 = time.time()
    with torch.no_grad():
        out_ids = MODEL.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=0.01,
        )
    dt = time.time() - t0

    input_len = inputs["input_ids"].shape[-1]
    gen_ids = out_ids[:, input_len:]
    text_out = PROCESSOR.batch_decode(gen_ids, skip_special_tokens=True)[0].strip()

    return {
        "ok": True,
        "latency_s": round(dt, 3),
        "text": text_out,
        "json": _jsonish(text_out),
    }


@APP.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": MODEL is not None,
        "base_model": BASE_MODEL,
        "adapter_path": ADAPTER_PATH,
        "uptime_s": round(time.time() - START_TS, 1),
        "cuda_available": torch.cuda.is_available(),
        "gpu_count": torch.cuda.device_count(),
    }


@APP.post("/infer")
async def infer_one(
    task: str = Form("perception"),
    goal: str = Form("explore the TV UI safely"),
    action: str = Form(""),
    image: UploadFile = File(...),
) -> JSONResponse:
    img = _load_image(await image.read())
    task = (task or "perception").strip().lower()

    base_prompt = PROMPTS.get(task, PROMPTS["perception"])
    if task == "policy":
        prompt = f"{base_prompt}\nGoal: {goal}"
    elif task == "verify":
        prompt = f"{base_prompt}\nRequested action: {action}"
    else:
        prompt = base_prompt

    result = infer([img], prompt)
    result.update({"task": task, "goal": goal, "action": action, "image_count": 1})
    return JSONResponse(result)


@APP.post("/verify")
async def verify_pair(
    action: str = Form(""),
    before: UploadFile = File(...),
    after: UploadFile = File(...),
) -> JSONResponse:
    before_img = _load_image(await before.read())
    after_img = _load_image(await after.read())
    prompt = f"{PROMPTS['verify']}\nRequested action: {action}"
    result = infer([before_img, after_img], prompt)
    result.update({"task": "verify", "action": action, "image_count": 2})
    return JSONResponse(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("ABOT_VLM_PORT", "8765")))
    parser.add_argument("--base-model", default=os.getenv("ABOT_VLM_BASE_MODEL", "Qwen/Qwen3-VL-8B-Instruct"))
    parser.add_argument(
        "--adapter",
        default=os.getenv(
            "ABOT_VLM_ADAPTER",
            "/home/montjac/aBotTesty_vlm_jobs/abot_vlm_20260527_120621/outputs/abot_vlm_20260527_120621",
        ),
    )
    args = parser.parse_args()

    load_model(args.base_model, args.adapter)

    import uvicorn

    uvicorn.run(APP, host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
