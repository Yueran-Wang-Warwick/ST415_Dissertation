# runtime.py
import time
from dataclasses import dataclass
from threading import Lock
from typing import Optional, Tuple

import torch
from datasets import Dataset

import SEDNA_BERT as bert
from transformers import AutoTokenizer, AutoModelForCausalLM, GenerationConfig

import config


@dataclass
class RuntimeState:
    sentiment_model: Optional[object] = None

    llama_tokenizer: Optional[object] = None
    llama_model: Optional[object] = None
    llama_config: Optional[object] = None

    llama_inputs_dir: Optional[str] = None
    llama_input_paths: Optional[dict] = None

    llama_inputs_dir: Optional[str] = None
    llama_input_paths: Optional[dict] = None


STATE = RuntimeState()

_LLAMA_JOB_LOCK = Lock()
_LLAMA_JOB_BUSY = False


def try_acquire_llama_job() -> bool:
    global _LLAMA_JOB_BUSY
    with _LLAMA_JOB_LOCK:
        if _LLAMA_JOB_BUSY:
            return False
        _LLAMA_JOB_BUSY = True
        return True


def release_llama_job() -> None:
    global _LLAMA_JOB_BUSY
    with _LLAMA_JOB_LOCK:
        _LLAMA_JOB_BUSY = False


def init_sedna_tokenizer() -> None:
    dummy = Dataset.from_dict(
        {"text": ["hello"], "label": [0], "title": [""], "Class": ["Meaningful"]}
    )

    bert.Apply_Tokenization(
        training_set=dummy,
        testing_set=dummy,
        tokenizer=config.BASE_MODEL,
    )


def init_sedna_device(model) -> None:
    bert.X_Entropy_Hypersetting(
        Sentiment_Model=model,
        lr=1e-5,
        optimizer_selected="adamw",
        device=config.DEVICE,
    )


def load_sentiment_model():
    return bert.Reload_Model(
        base_model=config.BASE_MODEL,
        model_dir=config.MODEL_PATH,
        device_selected=config.DEVICE,
    )


def load_llama_tokenizer() -> object:
    llama_tokenizer = AutoTokenizer.from_pretrained(config.LLAMA_DIR)

    llama_tokenizer.model_max_length = int(getattr(config, "LLAMA_MAX_CONTEXT", 4500))

    if llama_tokenizer.pad_token_id is None:
        llama_tokenizer.pad_token_id = llama_tokenizer.eos_token_id

    return llama_tokenizer


def load_llama_model() -> Tuple[object, object]:
    llama_model = AutoModelForCausalLM.from_pretrained(
        config.LLAMA_DIR,
        device_map="auto",
        dtype=torch.bfloat16,
    )

    llama_config = GenerationConfig.from_pretrained(config.LLAMA_DIR)

    return llama_model, llama_config


def load_llama() -> Tuple[object, object, object]:
    llama_tokenizer = load_llama_tokenizer()
    llama_model, llama_config = load_llama_model()
    return llama_tokenizer, llama_model, llama_config



_TOKENIZER_READY = False


def init_runtime() -> None:
    global _TOKENIZER_READY
    if _TOKENIZER_READY:
        return

    print(f"Device: {config.DEVICE}", flush=True)

    print("Initialising SEDNA tokenizer...", flush=True)
    t0 = time.time()
    init_sedna_tokenizer()
    print(f"Tokenizer ready in {time.time() - t0:.1f}s", flush=True)

    _TOKENIZER_READY = True


def ensure_sentiment_loaded() -> None:
    if STATE.sentiment_model is not None:
        return

    print("Loading DeBERTa model...", flush=True)
    t1 = time.time()
    STATE.sentiment_model = load_sentiment_model()
    print(f"DeBERTa loaded in {time.time() - t1:.1f}s", flush=True)

    print("Initialising SEDNA device state...", flush=True)
    t2 = time.time()
    init_sedna_device(STATE.sentiment_model)
    print(f"Device state ready in {time.time() - t2:.1f}s", flush=True)


def unload_sentiment_model() -> None:
    if STATE.sentiment_model is None:
        return

    try:
        del STATE.sentiment_model
    except Exception:
        pass

    STATE.sentiment_model = None

    import gc
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass


def ensure_llama_tokenizer_loaded() -> None:
    if STATE.llama_tokenizer is not None:
        return

    print("Loading Llama tokenizer...", flush=True)
    t = time.time()
    STATE.llama_tokenizer = load_llama_tokenizer()
    print(f"Llama tokenizer loaded in {time.time() - t:.1f}s", flush=True)


def ensure_llama_loaded() -> None:
    if STATE.llama_model is not None:
        return

    if STATE.llama_tokenizer is None:
        ensure_llama_tokenizer_loaded()

    print("Loading Llama model...", flush=True)
    t = time.time()
    STATE.llama_model, STATE.llama_config = load_llama_model()
    print(f"Llama loaded in {time.time() - t:.1f}s", flush=True)


def get_vram_status() -> dict:
    if not torch.cuda.is_available():
        return {"available": False, "used_gb": 0.0, "total_gb": 0.0, "pct": 0.0}

    try:
        free_b, total_b = torch.cuda.mem_get_info()
        used_b = total_b - free_b
    except Exception:
        total_b = int(torch.cuda.get_device_properties(0).total_memory)
        used_b = int(torch.cuda.memory_allocated(0))

    used_gb = float(used_b) / (1024.0 ** 3)
    total_gb = float(total_b) / (1024.0 ** 3)
    pct = 0.0 if total_gb <= 0 else (100.0 * used_gb / total_gb)

    return {
        "available": True,
        "used_gb": used_gb,
        "total_gb": total_gb,
        "pct": pct,
    }
