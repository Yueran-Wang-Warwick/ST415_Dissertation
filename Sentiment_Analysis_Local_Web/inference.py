# inference.py
import io
import json
import re
from contextlib import redirect_stdout
from threading import Thread
from typing import Iterator, Tuple

import SEDNA_BERT as bert
from transformers import TextIteratorStreamer

import config
import runtime


_PRED_RE = re.compile(
    r"Final Prediction:\s*([A-Za-z_]+)\s*\|\s*Confidence\s*=\s*([0-9]*\.?[0-9]+)",
    re.IGNORECASE,
)


def infer_sentiment(text: str) -> Tuple[str, float, str]:
    runtime.ensure_sentiment_loaded()

    buf = io.StringIO()
    with redirect_stdout(buf):
        bert.Sentiment_Classification(
            text=text,
            BERT_Model=runtime.STATE.sentiment_model,
            Label_mapping=config.LABEL_MAPPING,
        )

    raw = buf.getvalue().strip()
    m = _PRED_RE.search(raw)
    if not m:
        return "Unknown", 0.0, raw

    return m.group(1), float(m.group(2)), raw


def infer_sentiment_batch(texts: list[str], max_length: int = 260) -> list[tuple[str, float]]:
    runtime.ensure_sentiment_loaded()

    if not texts:
        return []

    with redirect_stdout(io.StringIO()):
        results = bert.Sentiment_Classification(
            text=texts,
            BERT_Model=runtime.STATE.sentiment_model,
            Label_mapping=config.LABEL_MAPPING,
            max_length=max_length,
        )

    if isinstance(results, tuple):
        results = [results]

    out: list[tuple[str, float]] = []
    for pred, conf in results:
        out.append((str(pred), float(conf)))
    return out


def iter_llama_summary_chunks(text: str) -> Iterator[str]:
    tk = runtime.STATE.llama_tokenizer
    model = runtime.STATE.llama_model
    gen_cfg = runtime.STATE.llama_config

    conversation = [
        {"role": "system", "content": config.SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]

    input_ids = tk.apply_chat_template(
        conversation,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    streamer = TextIteratorStreamer(
        tk,
        skip_prompt=True,
        skip_special_tokens=True,
    )

    gen_kwargs = {
        "input_ids": input_ids,
        "generation_config": gen_cfg,
        "attention_mask": input_ids.ne(tk.pad_token_id),
        "streamer": streamer,
        "do_sample": False,
        "max_new_tokens": 180,
    }

    Thread(target=model.generate, kwargs=gen_kwargs).start()

    for piece in streamer:
        yield piece


def sse_pack_text_piece(piece: str) -> str:
    return f"data: {json.dumps({'t': piece}, ensure_ascii=False)}\n\n"
