import functools

import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, T5EncoderModel

MODEL_NAME = "Salesforce/codet5p-220m"
CHUNK_SIZE = 1000
MAX_LENGTH = 512


@functools.lru_cache(maxsize=1)
def _load_model() -> tuple:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = T5EncoderModel.from_pretrained(MODEL_NAME)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()
    return tokenizer, model, device


def _embed(text: str) -> torch.Tensor | None:
    if not text or not text.strip():
        return None

    tokenizer, model, device = _load_model()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_LENGTH,
        padding=True,
    ).to(device)

    with torch.no_grad():
        hidden = model(**inputs).last_hidden_state

    mask = inputs["attention_mask"].unsqueeze(-1).float()
    emb = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    return emb  # (1, hidden_dim)


def _chunks(text: str) -> list[str]:
    return [text[i : i + CHUNK_SIZE] for i in range(0, len(text), CHUNK_SIZE)]


def compute_similarity(message: str, diff: str) -> float:
    """Return cosine similarity in [0, 1] between a commit message and its diff."""
    if not message or not message.strip():
        return 0.0
    if not diff or not diff.strip():
        return 0.0

    msg_emb = _embed(message)
    if msg_emb is None:
        return 0.0

    best = 0.0
    for chunk in _chunks(diff):
        chunk_emb = _embed(chunk)
        if chunk_emb is None:
            continue
        score = max(0.0, F.cosine_similarity(msg_emb, chunk_emb).item())
        if score > best:
            best = score

    return round(best, 6)