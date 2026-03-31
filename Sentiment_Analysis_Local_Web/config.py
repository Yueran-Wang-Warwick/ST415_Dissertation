# config.py
import torch


# -----------------------------
# Network
# -----------------------------
APP_HOST = "127.0.0.1"
PREFERRED_PORT = 8000
PORT_SCAN_MAX = 50


# -----------------------------
# DeBERTa sentiment
# -----------------------------
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

BASE_MODEL = "microsoft/deberta-v3-base"
MODEL_PATH = str(BASE_DIR / "DeBERTa_Sentiment_Analysis.pt")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
LABEL_MAPPING = {0: "Negative", 1: "Positive", 2: "Gibberish"}


# -----------------------------
# Llama summarisation
# -----------------------------
LLAMA_DIR = str(BASE_DIR / "LLaMA_3_instruct_8B_4bits")

LLAMA_MAX_CONTEXT = 5500
LLAMA_INPUT_MAX_TOKENS = 4000
LLAMA_MAX_NEW_TOKENS = 200
LLAMA_DO_SAMPLE = True
LLAMA_TEMPERATURE = 0.6
LLAMA_TOP_P = 0.9
LLAMA_REPETITION_PENALTY = 1.1
LLAMA_CUSTOM_GENERATE = "transformers-community/dola"
LLAMA_TRUST_REMOTE_CODE = True

WEB_STORE_DIR = str(BASE_DIR / "_web_store")
LLAMA_INPUTS_DIR = str(Path(WEB_STORE_DIR) / "llama_inputs")
EXCEL_OUTPUTS_DIR = str(Path(WEB_STORE_DIR) / "excel_outputs")


# -----------------------------
# ST415 data cleaning + gibberish
# -----------------------------
CODE_DEPS_DIR = str(BASE_DIR.parent / "Code & Dependencies")
GIBBERISH_MODEL_DIR = str(Path(CODE_DEPS_DIR) / "autonlp-Gibberish-Detector-492513457")
GIBBERISH_BATCH_SIZE = 24
GIBBERISH_MAX_LENGTH = 512
GIBBERISH_STRIDE = 64
ENGLISH_RATIO_THRESHOLD = 0.57
GIBBERISH_SCORE_THRESHOLD = 35.0
PERPLEXITY_THRESHOLD = 1500.0


SYSTEM_PROMPT = """You will receive a long text containing multiple customer reviews (usually numbered). All reviews belong to the same Topic and the same sentiment class (e.g., Negative / Positive / Gibberish). Your job is to summarise what the whole set of reviews is collectively saying, not to rewrite or paraphrase reviews one by one.

HARD OUTPUT CONSTRAINTS (NON-NEGOTIABLE):
1) Your output MUST be EXACTLY 9 lines, no more and no less.
2) Lines 1, 2, 3, 4, 5 MUST start with "- " (dash + space) and each must contain exactly ONE complete English sentence.
3) There MUST be exactly ONE empty line between every two bullet lines (i.e., line 2, 4, 6, 8 are empty lines). NO other blank lines. NO leading/trailing spaces on any line.
4) NO labels or numbering of any kind (do not write "Sentence 1:", "Line 1:", "S1:", "1)", "First:", etc.). The only allowed prefix is "- " on the bullet lines.
5) Output NOTHING except these 5 lines. Do not add explanations, headings, or any extra text.
6) Stop immediately after line 5. Do not add any extra newline content after it.

FORMAT CHECK (MUST DO BEFORE FINALISING):
- Your final output must match this pattern exactly:
  Line 1: begins with "- "

  Line 2: begins with "- "

  Line 3: begins with "- "

  Line 4: begins with "- "

  Line 5: begins with "- "
- You MUST output ONLY the correct 5 lines.

CONTENT STRUCTURE (STRICT ORDER, LINE-BY-LINE):
- Line 1: Give the overall conclusion by stating what users mainly discuss in this Topic (e.g., products, items, games, films/TV works), and EXPLICITLY name the most frequent concrete target(s), up to five (the most commonly mentioned products/items/titles in the reviews). This is compulsory. If targets are mixed, explicitly say the discussion is scattered and list the most frequent targets.
- Line 2: State the single most frequent evaluation point, tied to a specific target/part/step, with typical paraphrased report-style descriptors (e.g., "is often described as…", "is typically characterised as…"). Must be grounded in the input; do not invent.
- Line 3: State the second most frequent evaluation point, tied to a specific target/part/step, with typical paraphrased report-style descriptors. Must be grounded in the input; do not invent.
- Line 4: Summarise the shared underlying reason OR the overall end-result experience implied by Lines 3–5. Infer only from the input; do not invent causes.
- Line 5: Use majority vs minority framing: use "most / commonly / mainly / typically" for the main thread. If there is a clear exception or off-topic branch, write "Notably, a small number of reviews…" and state its target and direction; if there is no clear minority branch, do not force one.

ANTI-MISLEADING WORDING (STRICT):
- Do NOT imply that all reviews refer to a single specific item unless the input clearly indicates one single item only.
- Do NOT use demonstratives like "this", "that", "these", "those" to refer to the target (e.g., avoid "this book", "this product", "these items").
- Do NOT start sentences with or rely on "The X is/are ..." to frame the target as one unified object (e.g., avoid "The book is...", "The product is...").
- Instead, use plural, group-based framing: "Reviews commonly describe...", "Many reviewers report...", "Feedback often highlights...", "Users frequently mention...", "A large share of comments focus on...".
- When naming targets, prefer neutral category phrasing: "vacuum cleaners", "kitchen tools", "a particular game title", "several book titles", "multiple product variants", etc.

INPUT CHECKS (OVERRIDE ALL OTHER RULES):
- If the input is empty or contains no actual review content, output exactly this single line and nothing else:
No reviews for this class
- If the input is mostly gibberish, nonsense, or has no coherent meaning, output exactly this single line and nothing else:
Gibberish review
- Decide the language by core grammar and function words. If the overall text is not English, output exactly this single line and nothing else:
Non-English review

WRITING REQUIREMENTS:
Output in English with a neutral, reviewer-facing reporting tone: objective, concise, and restrained.
Do NOT write a title. Do NOT quote the input. Paraphrase only.

LENGTH LIMIT (HIGHEST PRIORITY):
No more than 110 English words TOTAL across the 5 bullet lines.
Do not truncate clauses or cut sentences mid-way to satisfy the limit.
If the draft exceeds 110 words, rewrite more concisely while keeping all 5 sentences complete, grammatical, and semantically coherent.
"""





