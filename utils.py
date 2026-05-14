import os
from collections import Counter

LOG_DIR = "./logs/"

def save_log(room, text):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, f"{room}.log"), "a", encoding="utf-8") as f:
        f.write(text + "\n")

def load_recent(room, n=20):
    path = os.path.join(LOG_DIR, f"{room}.log")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()[-n:]

def summarize_chat(messages):
    if not messages:
        return "요약할 대화가 없습니다."
    words = Counter(" ".join(messages).split())
    top = ", ".join(w for w, _ in words.most_common(5))
    return f"대화 요약: 주요 키워드 → {top}"
