# topic_summary.py
import os
from typing import Iterator, Optional

import inference
import runtime


def _resolve_llama_input_path(topic_id: str, cls: str) -> Optional[str]:
    mp = runtime.STATE.llama_input_paths or {}

    tid_int = None
    try:
        tid_int = int(topic_id)
    except Exception:
        tid_int = None

    cls = str(cls or "Positive").strip() or "Positive"

    if tid_int is not None:
        per = mp.get(tid_int)
        if per and isinstance(per, dict):
            return per.get(cls)

    per = mp.get(str(topic_id))
    if per and isinstance(per, dict):
        return per.get(cls)

    return None


def iter_topic_summary_sse(topic_id: str, cls: str) -> Iterator[str]:
    runtime.ensure_llama_loaded()

    path = _resolve_llama_input_path(topic_id, cls)
    text = ""
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

    if not str(text).strip():
        yield inference.sse_pack_text_piece("该Class没有对应评论")
        yield "data: [DONE]\n\n"
        return

    for piece in inference.iter_llama_summary_chunks(text):
        yield inference.sse_pack_text_piece(piece)

    yield "data: [DONE]\n\n"
