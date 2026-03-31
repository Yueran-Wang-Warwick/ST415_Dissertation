# llama_input_prep.py
from __future__ import annotations

import os
from typing import Dict, List

import numpy as np


def count_tokens(tokenizer, text: str) -> int:
    if not text:
        return 0
    ids = tokenizer.encode(text, add_special_tokens=False)
    return len(ids)


def truncate_to_tokens(tokenizer, text: str, max_tokens: int) -> str:
    if not text or max_tokens <= 0:
        return ""
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= max_tokens:
        return text
    return tokenizer.decode(ids[:max_tokens], skip_special_tokens=True)


def mmr_select(
    cand_emb: np.ndarray,
    query_emb: np.ndarray,
    k: int,
    lambda_mmr: float,
) -> List[int]:
    n = int(cand_emb.shape[0])
    if n == 0:
        return []
    if k >= n:
        return list(range(n))

    q = query_emb / (np.linalg.norm(query_emb) + 1e-12)
    sim_to_q = cand_emb @ q

    selected = [int(np.argmax(sim_to_q))]
    remaining = np.ones(n, dtype=bool)
    remaining[selected[0]] = False

    sim_mat = cand_emb @ cand_emb.T

    while len(selected) < k:
        rem = np.where(remaining)[0]
        max_sim_sel = sim_mat[rem][:, selected].max(axis=1)
        score = lambda_mmr * sim_to_q[rem] - (1.0 - lambda_mmr) * max_sim_sel
        pick = int(rem[int(np.argmax(score))])
        selected.append(pick)
        remaining[pick] = False

    return selected


def _centroid(emb_norm: np.ndarray, doc_ids: np.ndarray) -> np.ndarray:
    cent = emb_norm[doc_ids].mean(axis=0)
    cent = cent / (np.linalg.norm(cent) + 1e-12)
    return cent


def _core_far_candidates(
    emb_norm: np.ndarray,
    doc_ids: np.ndarray,
    cent: np.ndarray,
    core_n: int,
    far_n: int,
) -> np.ndarray:
    E = emb_norm[doc_ids]
    sims = E @ cent

    core = doc_ids[np.argsort(-sims)[: min(core_n, doc_ids.size)]]
    far = doc_ids[np.argsort(sims)[: min(far_n, doc_ids.size)]]
    cand = np.unique(np.concatenate([core, far]).astype(int))
    return cand


def _build_llama_text(
    tokenizer,
    topic_id: int,
    label: str,
    picked_ids: np.ndarray,
    docs: List[str],
    max_tokens: int,
) -> str:
    header = f"Topic {topic_id} | {label} reviews\n\n"
    used = count_tokens(tokenizer, header)
    if used >= max_tokens:
        return truncate_to_tokens(tokenizer, header, max_tokens)

    pieces: List[str] = [header]
    idx = 1

    for did in picked_ids:
        t = docs[int(did)].strip()
        if not t:
            continue

        block = f"{idx}. {t}\n\n"
        need = count_tokens(tokenizer, block)

        if used + need > max_tokens:
            break

        pieces.append(block)
        used += need
        idx += 1

        if used >= max_tokens:
            break

    out = "".join(pieces)
    return truncate_to_tokens(tokenizer, out, max_tokens)


def _select_for_label(
    emb_norm: np.ndarray,
    docs: List[str],
    sent_labels: List[str],
    cand_ids: np.ndarray,
    cent: np.ndarray,
    topic_id: int,
    label: str,
    max_tokens: int,
    k_target: int,
    min_for_mmr: int,
    mmr_lambda: float,
    tokenizer,
) -> str:
    bucket_ids = np.array([i for i in cand_ids if sent_labels[int(i)] == label], dtype=int)
    if bucket_ids.size == 0:
        return ""

    bucket_emb = emb_norm[bucket_ids]

    if bucket_ids.size >= min_for_mmr:
        picked_local = mmr_select(bucket_emb, cent, min(k_target, bucket_ids.size), mmr_lambda)
        picked_ids = bucket_ids[np.array(picked_local, dtype=int)]
    else:
        sims = bucket_emb @ cent
        order = np.argsort(-sims)
        picked_ids = bucket_ids[order[: min(k_target, bucket_ids.size)]]

    return _build_llama_text(
        tokenizer=tokenizer,
        topic_id=topic_id,
        label=label,
        picked_ids=picked_ids,
        docs=docs,
        max_tokens=max_tokens,
    )


def prepare_all_topics(
    *,
    docs: List[str],
    sent_labels: List[str],
    topics: np.ndarray,
    emb_norm: np.ndarray,
    tokenizer,
    out_dir: str,
    max_tokens: int,
    core_n: int = 220,
    far_n: int = 220,
    k_target: int = 80,
    min_for_mmr: int = 30,
    mmr_lambda: float = 0.65,
) -> Dict[int, Dict[str, str]]:
    os.makedirs(out_dir, exist_ok=True)

    topic_ids = sorted(int(t) for t in set(topics.tolist()) if int(t) != -1)
    out_paths: Dict[int, Dict[str, str]] = {}

    for tid in topic_ids:
        doc_ids = np.where(topics == tid)[0]
        if doc_ids.size == 0:
            continue

        cent = _centroid(emb_norm, doc_ids)
        cand_ids = _core_far_candidates(emb_norm, doc_ids, cent, core_n=core_n, far_n=far_n)

        per_label: Dict[str, str] = {}
        for label in ["Positive", "Negative"]:
            txt = _select_for_label(
                emb_norm=emb_norm,
                docs=docs,
                sent_labels=sent_labels,
                cand_ids=cand_ids,
                cent=cent,
                topic_id=tid,
                label=label,
                max_tokens=max_tokens,
                k_target=k_target,
                min_for_mmr=min_for_mmr,
                mmr_lambda=mmr_lambda,
                tokenizer=tokenizer,
            )

            fname = f"{label}_llama_input_{tid}.txt"
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(txt)

            per_label[label] = fpath

        out_paths[tid] = per_label

    return out_paths
