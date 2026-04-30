import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, T5EncoderModel
import functools

MODEL_NAME = "Salesforce/codet5p-220m"



@functools.lru_cache(maxsize=1)
def _load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model  = T5EncoderModel.from_pretrained(MODEL_NAME)
    device    = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.eval()
    return tokenizer, model, device




def _embed(text: str):
    if not text or not text.strip():
        return None

    tokenizer, model, device = _load_model()

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True,
    ).to(device)

    with torch.no_grad():
        outputs = model(**inputs)

    hidden = outputs.last_hidden_state                     
    mask   = inputs["attention_mask"].unsqueeze(-1).float() 
    emb    = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
    return emb  # (1, hidden)




def _chunk(text: str, size: int = 1000) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]




def compute_similarity(message: str, diff: str) -> float:

    if not message or not message.strip():
        return 0.0
    if not diff or not diff.strip():
        return 0.0

    msg_emb = _embed(message)
    if msg_emb is None:
        return 0.0

    best = 0.0
    for chunk in _chunk(diff):
        chunk_emb = _embed(chunk)
        if chunk_emb is None:
            continue
        score = F.cosine_similarity(msg_emb, chunk_emb).item()
        score = max(0.0, score)
        if score > best:
            best = score

    return round(best, 6)