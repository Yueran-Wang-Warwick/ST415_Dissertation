import gc
import io
import math
import os
import re
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterator, Optional

import pandas as pd
import torch
import torch.nn.functional as F

import config


_URL_RE = re.compile(r"(?:https?://\S+|www\.\S+)")
_HTML_RE = re.compile(r"<.*?>")
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"
    "\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF"
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)
_GLITCH_RE = re.compile(r"[^A-Za-z0-9\s.,!?;:'\"()\[\]\-\/&%$#@*+=_~`]")
_SPACE_RE = re.compile(r"\s+")


_GIB_PIPE = None
_GIB_WEIGHT_BY_ID = None
_ENGLISH_VOCAB = None
_ENGLISH_CACHE: Dict[str, bool] = {}
_PPL_TOKENIZER = None
_PPL_MODEL = None
_PPL_DEVICE = None

_JOB_LOCK = Lock()
_JOB_BUSY = False

_OUTPUT_LOCK = Lock()
_OUTPUT_FILES: Dict[str, Dict[str, Any]] = {}


def try_acquire_job() -> bool:
    global _JOB_BUSY
    with _JOB_LOCK:
        if _JOB_BUSY:
            return False
        _JOB_BUSY = True
        return True


def release_job() -> None:
    global _JOB_BUSY
    with _JOB_LOCK:
        _JOB_BUSY = False


def _event_log(message: str) -> Dict[str, Any]:
    return {"type": "log", "message": str(message)}


def _sanitize_stem(name: str) -> str:
    stem = Path(name or "uploaded").stem.strip() or "uploaded"
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem)
    stem = stem.strip("._") or "uploaded"
    return stem


def _is_missing(v: Any) -> bool:
    try:
        return bool(pd.isna(v))
    except Exception:
        return False


def _changed_count(before: list[Any], after: list[Any]) -> int:
    changed = 0
    for b, a in zip(before, after):
        if _is_missing(b) and _is_missing(a):
            continue
        if str(b) != str(a):
            changed += 1
    return changed


def _remove_url(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return _URL_RE.sub("", text)


def _remove_html(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return _HTML_RE.sub("", text)


def _remove_emoji(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    return _EMOJI_RE.sub("", text)


def _glitch_clean_text(text: Any) -> Any:
    if not isinstance(text, str):
        return text
    cleaned = _GLITCH_RE.sub("", text)
    cleaned = _SPACE_RE.sub(" ", cleaned).strip()
    return cleaned


def _dedup_text(text: Any, window: int = 10, repeat_threshold: int = 3) -> Any:
    if not isinstance(text, str):
        return text

    text = re.sub(r"([!?.,])\1{2,}", r"\1\1", text)
    text = re.sub(r"([a-zA-Z])\1{2,}", r"\1\1", text)
    text = re.sub(r"\b(\w+)( \1\b)+", r"\1", text)

    words = text.split()
    cleaned_words = []
    recent: list[str] = []

    for w in words:
        recent.append(w)
        if len(recent) > window:
            recent.pop(0)
        freq = Counter([r.lower() for r in recent])
        if freq[w.lower()] >= repeat_threshold:
            continue
        cleaned_words.append(w)

    out = " ".join(cleaned_words)
    out = _SPACE_RE.sub(" ", out).strip()
    return out


def _read_excel_bytes(raw: bytes) -> pd.DataFrame:
    try:
        return pd.read_excel(io.BytesIO(raw))
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}") from e


def _read_csv_bytes(raw: bytes) -> pd.DataFrame:
    def _looks_headerless(cols: list[str]) -> bool:
        if not cols:
            return False

        numeric_cols = 0
        long_cols = 0
        sentence_cols = 0
        for c in cols:
            s = str(c or "").strip()
            if re.fullmatch(r"-?\d+(\.\d+)?", s):
                numeric_cols += 1
            if len(s) >= 30:
                long_cols += 1
            if (" " in s) and (len(s) >= 12):
                sentence_cols += 1

        return (numeric_cols >= 1 and (long_cols >= 1 or sentence_cols >= 1)) or (long_cols >= 2)

    def _assign_default_no_header_names(df: pd.DataFrame) -> pd.DataFrame:
        cols = []
        for i in range(df.shape[1]):
            if i == 0:
                cols.append("label")
            elif i == 1:
                cols.append("title")
            elif i == 2:
                cols.append("text")
            else:
                cols.append(f"col_{i+1}")
        out = df.copy()
        out.columns = cols
        return out

    last_err: Optional[Exception] = None
    for enc in ["utf-8-sig", "utf-8", "cp1252", "latin1"]:
        try:
            df_head = pd.read_csv(io.BytesIO(raw), encoding=enc)
        except Exception as e:
            last_err = e
            continue

        named_text = _find_col(df_head, ["text", "comment", "comments", "review", "content"])
        if named_text is not None:
            return df_head

        col_names = [str(c) for c in df_head.columns]
        if _looks_headerless(col_names):
            try:
                df_no_head = pd.read_csv(io.BytesIO(raw), encoding=enc, header=None)
                return _assign_default_no_header_names(df_no_head)
            except Exception as e:
                last_err = e
                continue

        return df_head

    raise ValueError(f"Failed to read CSV file: {last_err}")


def _read_table_bytes(raw: bytes, filename: str) -> tuple[pd.DataFrame, str]:
    suffix = Path(filename or "").suffix.lower()
    if suffix in [".xlsx", ".xlsm"]:
        return _read_excel_bytes(raw), "excel"
    if suffix == ".csv":
        return _read_csv_bytes(raw), "csv"
    raise ValueError("Unsupported file extension. Please upload .csv, .xlsx, or .xlsm.")


def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[Any]:
    lower_to_col = {str(c).strip().lower(): c for c in df.columns}
    for k in candidates:
        if k in lower_to_col:
            return lower_to_col[k]

    for col in df.columns:
        s = str(col).strip().lower()
        for k in candidates:
            if k in s:
                return col
    return None


def _resolve_columns(df: pd.DataFrame) -> tuple[Any, Optional[Any], Optional[Any]]:
    text_col = _find_col(df, ["text", "comment", "comments", "review", "content"])
    if text_col is None:
        cols = list(df.columns)
        if len(cols) >= 3:
            return cols[2], cols[1], cols[0]
        if len(cols) == 2:
            return cols[1], None, cols[0]
        if len(cols) == 1:
            return cols[0], None, None
        raise ValueError(
            "No text/comment column was found. Expected one of: text, comment, review, content."
        )

    title_col = _find_col(df, ["title", "subject", "heading", "headline"])
    label_col = _find_col(df, ["label", "sentiment_label", "y"])
    return text_col, title_col, label_col


def _ensure_gibberish_runtime() -> None:
    global _GIB_PIPE, _GIB_WEIGHT_BY_ID
    if _GIB_PIPE is not None and _GIB_WEIGHT_BY_ID is not None:
        return

    if not os.path.isdir(config.GIBBERISH_MODEL_DIR):
        raise FileNotFoundError(
            f"Gibberish model folder not found: {config.GIBBERISH_MODEL_DIR}"
        )

    from transformers import pipeline as hf_pipeline

    device = 0 if torch.cuda.is_available() else -1
    _GIB_PIPE = hf_pipeline(
        "text-classification",
        model=config.GIBBERISH_MODEL_DIR,
        tokenizer=config.GIBBERISH_MODEL_DIR,
        device=device,
    )

    label2weight = {
        "clean": 0.0,
        "mild gibberish": 15.0,
        "word salad": 20.0,
        "noise": 60.0,
    }

    id2label = dict(getattr(_GIB_PIPE.model.config, "id2label", {}))
    num_labels = int(getattr(_GIB_PIPE.model.config, "num_labels", len(id2label) or 1))
    _GIB_WEIGHT_BY_ID = torch.zeros(
        num_labels, dtype=torch.float32, device=_GIB_PIPE.model.device
    )

    for i, name in id2label.items():
        norm = str(name).strip().lower().replace("_", " ").replace("-", " ")
        _GIB_WEIGHT_BY_ID[int(i)] = float(label2weight.get(norm, 0.0))


def _gibberish_score(text: Any) -> float:
    if not isinstance(text, str) or not text.strip():
        return 100.0

    _ensure_gibberish_runtime()

    tokens = _GIB_PIPE.tokenizer(
        text,
        truncation=True,
        max_length=int(getattr(config, "GIBBERISH_MAX_LENGTH", 512)),
        stride=int(getattr(config, "GIBBERISH_STRIDE", 64)),
        return_overflowing_tokens=True,
    )

    chunk_ids = list(tokens.get("input_ids", []))
    if not chunk_ids:
        chunk_ids = [
            _GIB_PIPE.tokenizer.encode(
                text,
                truncation=True,
                max_length=int(getattr(config, "GIBBERISH_MAX_LENGTH", 512)),
            )
        ]

    sub_scores = []
    for ids in chunk_ids:
        chunk_text = _GIB_PIPE.tokenizer.decode(ids, skip_special_tokens=True)

        with torch.no_grad():
            inputs = _GIB_PIPE.tokenizer(
                chunk_text,
                return_tensors="pt",
                truncation=True,
                max_length=int(getattr(config, "GIBBERISH_MAX_LENGTH", 512)),
            )
            inputs = {k: v.to(_GIB_PIPE.model.device) for k, v in inputs.items()}
            outputs = _GIB_PIPE.model(**inputs)
            probs = F.softmax(outputs.logits, dim=-1)[0]
            gib_score = float((probs * _GIB_WEIGHT_BY_ID).sum().item())
            sub_scores.append(gib_score)

    final_score = sum(sub_scores) / max(1, len(sub_scores))
    scaled = (final_score / 60.0) * 100.0
    return float(max(0.0, min(100.0, scaled)))


def _ensure_english_vocab() -> None:
    global _ENGLISH_VOCAB
    if _ENGLISH_VOCAB is not None:
        return

    deps = str(getattr(config, "CODE_DEPS_DIR", "")).strip()
    if deps and deps not in sys.path:
        sys.path.append(deps)

    from english_words import get_english_words_set

    _ENGLISH_VOCAB = get_english_words_set(["web2"], lower=True)


def _english_ratio(text: Any) -> float:
    if not isinstance(text, str) or not text.strip():
        return 0.0

    _ensure_english_vocab()

    words = re.findall(r"[A-Za-z]+", text.lower())
    if not words:
        return 0.0

    valid = 0
    for w in words:
        if w in _ENGLISH_CACHE:
            is_eng = _ENGLISH_CACHE[w]
        else:
            is_eng = bool(w in _ENGLISH_VOCAB)
            _ENGLISH_CACHE[w] = is_eng
        if is_eng:
            valid += 1

    return float(valid / len(words))


def _ensure_perplexity_runtime() -> None:
    global _PPL_TOKENIZER, _PPL_MODEL, _PPL_DEVICE
    if _PPL_TOKENIZER is not None and _PPL_MODEL is not None and _PPL_DEVICE is not None:
        return

    from transformers import GPT2LMHeadModel, GPT2TokenizerFast

    _PPL_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    _PPL_TOKENIZER = GPT2TokenizerFast.from_pretrained("distilgpt2")
    _PPL_MODEL = GPT2LMHeadModel.from_pretrained("distilgpt2").to(_PPL_DEVICE)
    _PPL_MODEL.eval()


def _perplexity(text: Any) -> float:
    if not isinstance(text, str) or not text.strip():
        return float("inf")

    _ensure_perplexity_runtime()

    with torch.no_grad():
        enc = _PPL_TOKENIZER(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )
        enc = {k: v.to(_PPL_DEVICE) for k, v in enc.items()}
        out = _PPL_MODEL(**enc, labels=enc["input_ids"])
        loss = float(out.loss.item())
        return float(math.exp(loss))


def _is_valid_text(text: Any) -> bool:
    if text is None:
        return False
    if isinstance(text, float) and math.isnan(text):
        return False
    if not isinstance(text, str):
        return False
    if not text.strip():
        return False
    return True


def _unload_models() -> None:
    global _GIB_PIPE, _GIB_WEIGHT_BY_ID, _PPL_MODEL, _PPL_TOKENIZER, _PPL_DEVICE

    try:
        del _GIB_PIPE
    except Exception:
        pass
    try:
        del _GIB_WEIGHT_BY_ID
    except Exception:
        pass
    try:
        del _PPL_MODEL
    except Exception:
        pass
    try:
        del _PPL_TOKENIZER
    except Exception:
        pass

    _GIB_PIPE = None
    _GIB_WEIGHT_BY_ID = None
    _PPL_MODEL = None
    _PPL_TOKENIZER = None
    _PPL_DEVICE = None

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass


def _purge_old_outputs(max_age_s: int = 86400) -> None:
    now = time.time()
    stale_ids: list[str] = []

    with _OUTPUT_LOCK:
        for k, meta in _OUTPUT_FILES.items():
            created = float(meta.get("created", 0.0))
            if now - created > max_age_s:
                stale_ids.append(k)

        for k in stale_ids:
            meta = _OUTPUT_FILES.pop(k, None)
            if not meta:
                continue
            p = str(meta.get("path", ""))
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass


def _register_output(path: str, filename: str) -> str:
    job_id = uuid.uuid4().hex
    with _OUTPUT_LOCK:
        _OUTPUT_FILES[job_id] = {
            "path": str(path),
            "filename": str(filename),
            "created": time.time(),
        }
    return job_id


def get_output_file(job_id: str) -> Optional[Dict[str, str]]:
    with _OUTPUT_LOCK:
        meta = _OUTPUT_FILES.get(str(job_id))
        if not meta:
            return None
        return {
            "path": str(meta.get("path", "")),
            "filename": str(meta.get("filename", "processed_table.xlsx")),
        }


def iter_excel_cleaning_and_gibberish(
    table_bytes: bytes,
    filename: str,
) -> Iterator[Dict[str, Any]]:
    _purge_old_outputs()

    if not table_bytes:
        raise ValueError("Uploaded file is empty.")

    yield _event_log("Starting Data Cleaning")

    df, input_type = _read_table_bytes(table_bytes, filename)
    if df.empty:
        raise ValueError("The uploaded file has no rows.")

    text_col, title_col, label_col = _resolve_columns(df)
    yield _event_log(f"Loaded '{filename}' with {len(df):,} rows.")
    yield _event_log(f"Detected text column: {text_col}")

    work = df.copy()
    original_columns = list(work.columns)

    temp_title_col = None
    if title_col is None:
        temp_title_col = "__title__"
        while temp_title_col in work.columns:
            temp_title_col += "_x"
        work[temp_title_col] = ""
        title_col = temp_title_col
        yield _event_log("Detected title column: (not found, using empty title)")
    else:
        yield _event_log(f"Detected title column: {title_col}")

    if label_col is None:
        yield _event_log("Detected label column: (not found, label remap will be skipped)")
    else:
        yield _event_log(f"Detected label column: {label_col}")

    before = work[text_col].tolist()
    after = [_remove_url(v) for v in before]
    work[text_col] = after
    yield _event_log(f"1. URL has been removed. Modified rows: {_changed_count(before, after):,}")

    before = work[text_col].tolist()
    after = [_remove_html(v) for v in before]
    work[text_col] = after
    yield _event_log(f"2. HTML tags have been removed. Modified rows: {_changed_count(before, after):,}")

    before = work[text_col].tolist()
    after = [_remove_emoji(v) for v in before]
    work[text_col] = after
    yield _event_log(f"3. Emojis have been removed. Modified rows: {_changed_count(before, after):,}")

    glitch_changed_total = 0
    for col in [title_col, text_col]:
        before = work[col].tolist()
        after = [_glitch_clean_text(v) for v in before]
        work[col] = after
        glitch_changed_total += _changed_count(before, after)
    yield _event_log(
        f"4. Garbled symbols have been cleaned on title/text. Modified cells: {glitch_changed_total:,}"
    )

    dedup_changed_total = 0
    for col in [title_col, text_col]:
        before = work[col].tolist()
        after = [_dedup_text(v) for v in before]
        work[col] = after
        dedup_changed_total += _changed_count(before, after)
    yield _event_log(f"5. Repeated patterns have been deduplicated. Modified cells: {dedup_changed_total:,}")

    valid_mask = work[text_col].apply(_is_valid_text)
    removed = int((~valid_mask).sum())
    if removed > 0:
        work = work[valid_mask].reset_index(drop=True)
    yield _event_log(
        f"6. Invalid text rows removed: {removed:,}. Remaining rows: {len(work):,}"
    )

    if temp_title_col and temp_title_col in work.columns:
        work = work.drop(columns=[temp_title_col])

    keep_cols = [c for c in original_columns if c in work.columns]
    if keep_cols:
        work = work.loc[:, keep_cols]

    out_dir = Path(getattr(config, "EXCEL_OUTPUTS_DIR", "./_web_store/excel_outputs"))
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_stem = _sanitize_stem(filename)
    out_name = f"{safe_stem}_clean.csv"

    out_path = out_dir / f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{out_name}"

    try:
        work.to_csv(out_path, index=False, header=False, encoding="utf-8-sig")
    except Exception as e:
        raise RuntimeError(f"Failed to write output file: {e}") from e

    job_id = _register_output(str(out_path), out_name)

    _unload_models()

    yield _event_log("File has been processed. Please click Download")
    yield {
        "type": "done",
        "job_id": job_id,
        "download_url": f"/api/excel_download/{job_id}",
        "filename": out_name,
        "rows": int(len(work)),
    }
