# csv_nlp.py
import io
import re
from collections import Counter
from typing import Any, Dict, List, Tuple, Iterator

import numpy as np

import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
import umap
import hdbscan

import gc
import os
import time

import torch

import config
import inference
import runtime
import llama_input_prep

_EMBEDDER = None

# Notebook-configured extra stops for BERTopic keyword quality
_DEFAULT_EXTRA_STOPS = [
    "lovely", "great", "good", "nice", "perfect", "excellent", "beautiful",
    "amazing", "brilliant", "wonderful", "fantastic", "gorgeous", "superb",
    "awesome", "happy", "pleased", "delighted",
    "thank", "thanks", "love", "loved", "like", "liked",
    "product", "item", "buy", "bought", "purchase", "ordered", "order",
    "really", "very", "highly", "absolutely", "totally", "definitely",
    "recommend", "recommended", "exactly", "just", "also", "bit",
    "quality",
]


def _normalise_plurals(words: List[str]) -> List[str]:
    word_set = set(words)
    to_remove = set()
    for w in words:
        if w + "s" in word_set or w + "es" in word_set:
            to_remove.add(w)
        if w.endswith("ies") and w[:-3] + "y" in word_set:
            to_remove.add(w[:-3] + "y")
    return [w for w in words if w not in to_remove]


def _dedup_keywords(phrases: List[str]) -> List[str]:
    cleaned = []
    for phrase in phrases:
        tokens = phrase.split()
        if len(tokens) == 2 and tokens[0] == tokens[1]:
            continue
        cleaned.append(phrase)
    all_words: List[str] = []
    for phrase in cleaned:
        all_words.extend(phrase.split())
    all_words = list(dict.fromkeys(all_words))
    all_words = _normalise_plurals(all_words)
    normalised_set = set(all_words)
    seen_words = set()
    kept = []
    for phrase in sorted(cleaned, key=lambda p: len(p.split())):
        tokens = [t for t in phrase.split() if t in normalised_set]
        if not tokens:
            continue
        word_set = set(tokens)
        if word_set <= seen_words:
            continue
        kept.append(" ".join(tokens))
        seen_words |= word_set
    return kept


def _excel_col_to_index(col: str) -> int:
    s = str(col).strip().upper()
    if not re.fullmatch(r"[A-Z]+", s or ""):
        raise ValueError("Column must be Excel-style letters like A, B, Z, AA, AB.")
    idx = 0
    for ch in s:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx - 1


def _get_embedder(device: str) -> SentenceTransformer:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = SentenceTransformer("all-mpnet-base-v2", device=device)
    return _EMBEDDER


def _unload_embedder() -> None:
    global _EMBEDDER
    if _EMBEDDER is None:
        return

    try:
        del _EMBEDDER
    except Exception:
        pass

    _EMBEDDER = None

    import gc
    gc.collect()

    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        try:
            torch.cuda.ipc_collect()
        except Exception:
            pass


def _confidence_dist(confs_by_cls: Dict[str, List[float]], bins: int = 50) -> Dict[str, Dict[str, List[float]]]:
    edges = np.linspace(0.0, 1.0, bins + 1)
    mids = ((edges[:-1] + edges[1:]) / 2.0).tolist()

    out: Dict[str, Dict[str, List[float]]] = {}
    for k, arr in confs_by_cls.items():
        if not arr:
            out[k] = {"x": mids, "y": [0.0] * bins}
            continue

        a = np.clip(np.asarray(arr, dtype=float), 0.0, 1.0)
        hist, _ = np.histogram(a, bins=edges)
        y = (hist / max(1, len(arr)) * 100.0).tolist()

        out[k] = {"x": mids, "y": [float(v) for v in y]}

    return out


def _build_topic_model(
    *,
    n_neighbors: int,
    n_components: int,
    min_dist: float,
    metric: str,
    min_cluster_size: int,
    min_samples: int,
    ngram_range: Tuple[int, int],
    min_df: int,
    max_df: float,
    top_n_words: int,
    extra_stops: List[str],
) -> BERTopic:
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    full_stops = list(ENGLISH_STOP_WORDS) + list(extra_stops)

    umap_model = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=min_dist,
        metric=metric,
        random_state=42,
    )

    hdbscan_model = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

    vectorizer_model = CountVectorizer(
        stop_words=full_stops,
        ngram_range=ngram_range,
        min_df=min_df,
        max_df=max_df,
    )

    return BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        top_n_words=top_n_words,
        calculate_probabilities=False,
        verbose=False,
    )


def _topic_name(topic_model: BERTopic, topic_id: int, topk: int = 4) -> str:
    words = topic_model.get_topic(topic_id) or []
    raw = [w for w, _ in words]
    deduped = _dedup_keywords(raw)[:topk]
    head = deduped if deduped else [w for w, _ in words[:topk]]
    return ", ".join(head) if head else f"Topic {topic_id}"


def iter_csv_analysis(csv_bytes: bytes, comment_col_letters: str) -> Iterator[Dict[str, Any]]:
    yield {"type": "progress", "p": 2, "stage": "Loading CSV"}

    for _enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(io.BytesIO(csv_bytes), encoding=_enc, header=None)
            break
        except UnicodeDecodeError:
            continue
    else:
        df = pd.read_csv(io.BytesIO(csv_bytes), encoding="latin-1", header=None)
    col_idx = _excel_col_to_index(comment_col_letters)

    if col_idx < 0 or col_idx >= df.shape[1]:
        raise ValueError(f"Column {comment_col_letters} is out of range for this CSV.")

    yield {"type": "progress", "p": 6, "stage": f"Selecting column {str(comment_col_letters).strip().upper()}"}

    texts_raw = df.iloc[:, col_idx].astype(str).tolist()
    texts_all = [t.strip() for t in texts_raw if isinstance(t, str) and t.strip()]

    total = len(texts_all)

    counts = Counter()
    preds_all: List[str] = []
    confs_by_cls = {"Positive": [], "Gibberish": [], "Negative": []}

    if total == 0:
        sentiment = {"Positive": 0, "Gibberish": 0, "Negative": 0, "Total": 0}
        yield {
            "type": "result",
            "p": 100,
            "sentiment": sentiment,
            "topics": [],
            "top_comments": {},
            "top_comments_by_class": {},
            "confidence_dist": _confidence_dist(confs_by_cls),
        }
        return

    yield {"type": "progress", "p": 10, "stage": "Loading DeBERTa Model"}
    runtime.ensure_sentiment_loaded()

    yield {"type": "progress", "p": 10, "stage": f"Running sentiment on {total} comments"}

    step = max(1, total // 50)

    batch_size = 48
    max_length = 260

    processed = 0
    next_tick = step

    for start in range(0, total, batch_size):
        batch_texts = texts_all[start : start + batch_size]
        batch_results = inference.infer_sentiment_batch(batch_texts, max_length=max_length)

        for pred, conf in batch_results:
            preds_all.append(pred)
            counts[pred] += 1

            if pred in confs_by_cls:
                confs_by_cls[pred].append(float(conf))

        processed += len(batch_texts)

        if (processed >= next_tick) or (processed == total):
            p = 10 + int(50 * processed / total)
            yield {"type": "progress", "p": p, "stage": f"Sentiment {processed}/{total}"}

            while next_tick <= processed:
                next_tick += step

    yield {"type": "progress", "p": 61, "stage": "Releasing DeBERTa Model"}
    runtime.unload_sentiment_model()

    sentiment = {
        "Positive": int(counts.get("Positive", 0)),
        "Gibberish": int(counts.get("Gibberish", 0)),
        "Negative": int(counts.get("Negative", 0)),
        "Total": int(total),
    }

    docs: List[str] = []
    docs_pred: List[str] = []
    for t, pred in zip(texts_all, preds_all):
        if len(t) > 10:
            docs.append(t)
            docs_pred.append(pred)

    yield {"type": "progress", "p": 62, "stage": "Loading Topic Embedder"}

    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedder = _get_embedder(device=device)

    yield {"type": "progress", "p": 66, "stage": "Embedding comments"}

    embeddings = embedder.encode(
        docs,
        batch_size=48,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    emb_norm = embeddings

    del embedder

    yield {"type": "progress", "p": 70, "stage": "Releasing Topic Embedder"}
    _unload_embedder()

    yield {"type": "progress", "p": 72, "stage": "Fitting BERTopic"}

    topic_model = _build_topic_model(
        n_neighbors=30,
        n_components=10,
        min_dist=0.1,
        metric="cosine",
        min_cluster_size=60,
        min_samples=5,
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.95,
        top_n_words=4,
        extra_stops=_DEFAULT_EXTRA_STOPS,
    )
    topics, probs = topic_model.fit_transform(docs, embeddings=embeddings)

    # Reduce outliers (not cached) to match notebook behaviour
    noise_before = sum(1 for t in topics if t == -1)
    if noise_before > 0:
        topics = topic_model.reduce_outliers(
            docs,
            topics,
            strategy="embeddings",
            embeddings=embeddings,
        )

    yield {"type": "progress", "p": 86, "stage": "Preparing topic summary"}

    topic_counts = Counter([t for t in topics if t != -1])

    topic_rows = []
    for tid, cnt in sorted(topic_counts.items(), key=lambda x: (-x[1], x[0])):
        topic_rows.append(
            {
                "topic_id": int(tid),
                "count": int(cnt),
                "name": _topic_name(topic_model, int(tid)),
            }
        )

    top_comments: Dict[str, List[str]] = {}
    if probs is None:
        probs = [None] * len(docs)

    per_topic_pairs: Dict[int, List[Tuple[float, str]]] = {}
    per_topic_pairs_by_class: Dict[int, Dict[str, List[Tuple[float, str]]]] = {}

    for t_id, text, pr, cls in zip(topics, docs, probs, docs_pred):
        if t_id == -1:
            continue

        score = 0.0
        if pr is not None:
            try:
                if np.isscalar(pr):
                    score = float(pr)
                else:
                    if hasattr(pr, "__len__") and len(pr) > int(t_id):
                        score = float(pr[int(t_id)])
                    else:
                        score = float(pr[0]) if len(pr) > 0 else 0.0
            except Exception:
                score = 0.0

        per_topic_pairs.setdefault(int(t_id), []).append((score, text))
        per_topic_pairs_by_class.setdefault(int(t_id), {}).setdefault(cls, []).append((score, text))

    for tid, pairs in per_topic_pairs.items():
        pairs.sort(key=lambda x: x[0], reverse=True)
        top_comments[str(tid)] = [t for _, t in pairs[:20]]

    top_comments_by_class: Dict[str, Dict[str, List[str]]] = {}
    for tid, m in per_topic_pairs_by_class.items():
        out: Dict[str, List[str]] = {}
        for cls in ["Positive", "Gibberish", "Negative"]:
            pairs = m.get(cls, [])
            pairs.sort(key=lambda x: x[0], reverse=True)
            out[cls] = [t for _, t in pairs[:20]]
        top_comments_by_class[str(tid)] = out

    yield {"type": "progress", "p": 88, "stage": "Releasing BERTopic"}
    del topic_model
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    yield {"type": "progress", "p": 90, "stage": "Loading Llama tokenizer"}
    runtime.ensure_llama_tokenizer_loaded()

    yield {"type": "progress", "p": 94, "stage": "Preparing Llama inputs"}
    topics_np = np.asarray(topics, dtype=int)

    run_id = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(config.LLAMA_INPUTS_DIR, run_id)

    paths = llama_input_prep.prepare_all_topics(
        docs=docs,
        sent_labels=docs_pred,
        topics=topics_np,
        emb_norm=emb_norm,
        tokenizer=runtime.STATE.llama_tokenizer,
        out_dir=out_dir,
        max_tokens=int(getattr(config, "LLAMA_INPUT_MAX_TOKENS", 4000)),
    )

    runtime.STATE.llama_inputs_dir = out_dir
    runtime.STATE.llama_input_paths = paths

    try:
        del embeddings
    except Exception:
        pass

    try:
        del emb_norm
    except Exception:
        pass

    try:
        del docs
    except Exception:
        pass

    try:
        del docs_pred
    except Exception:
        pass

    try:
        del topics_np
    except Exception:
        pass

    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    yield {"type": "progress", "p": 96, "stage": "Loading Llama model"}
    runtime.ensure_llama_loaded()

    yield {
        "type": "result",
        "p": 100,
        "sentiment": sentiment,
        "topics": topic_rows,
        "top_comments": top_comments,
        "top_comments_by_class": top_comments_by_class,
        "confidence_dist": _confidence_dist(confs_by_cls),
    }
