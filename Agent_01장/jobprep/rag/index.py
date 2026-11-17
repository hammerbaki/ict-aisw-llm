"""취업 자료(data/자료/*.md)의 검색 색인을 만들고 읽는다.

명령
    python -m rag.index                      # 색인을 새로 만든다
    python -m rag.index eval rag/평가문항.csv  # 상위 3개 재현율을 잰다

색인 파일의 위치는 환경 변수 RAG_INDEX_PATH로 바꿀 수 있다(기본 rag/index.json).
색인 파일은 자료에서 다시 만들 수 있는 산출물이므로 저장소에 넣지 않는다(.gitignore).
"""

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

from rag.chunker import chunk_markdown
from rag.embedder import choose_backend, embed, ollama_model
from rag.search import search

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "data" / "자료"

_cached = None  # 한 번 읽은 색인


def index_path():
    return Path(os.environ.get("RAG_INDEX_PATH", ROOT / "rag" / "index.json"))


def docs_fingerprint(docs_dir=DOCS_DIR):
    """자료 문서들의 내용으로 만든 지문. 문서가 바뀌면 값이 달라진다."""
    digest = hashlib.sha256()
    for path in sorted(docs_dir.glob("*.md")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()[:16]


def build_index(docs_dir=DOCS_DIR, path=None):
    """자료를 청크로 자르고 임베딩해 색인 파일로 저장한 뒤, 색인 dict를 돌려준다."""
    backend = choose_backend()
    chunks = []
    for doc in sorted(docs_dir.glob("*.md")):
        for chunk in chunk_markdown(doc.read_text(encoding="utf-8"), doc.name):
            chunk["vector"] = embed(chunk["text"], backend)
            chunks.append(chunk)
    index = {
        "backend": backend,
        "model": ollama_model() if backend == "ollama" else "bigram-hash",
        "fingerprint": docs_fingerprint(docs_dir),
        "chunks": chunks,
    }
    path = Path(path or index_path())
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)
    return index


def get_index():
    """색인을 돌려준다. 파일이 없거나, 자료가 바뀌었거나, 임베딩 방식이 다르면 새로 만든다."""
    global _cached
    if _cached is not None:
        return _cached
    path = index_path()
    if path.exists():
        with open(path, encoding="utf-8") as f:
            index = json.load(f)
        if index.get("fingerprint") == docs_fingerprint() and index.get("backend") == choose_backend():
            _cached = index
            return _cached
    _cached = build_index(path=path)
    return _cached


def recall_at_k(csv_path, index, k=3):
    """평가 문항(질문, 정답키워드)마다 상위 k개 청크에 정답 키워드가 있는지 보고 비율을 돌려준다."""
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    hits = []
    for row in rows:
        results = search(row["질문"], index, top_k=k)
        hits.append(any(row["정답키워드"] in item["chunk"]["text"] for item in results))
    return sum(hits) / len(rows), hits, rows


def main():
    if len(sys.argv) == 1:
        index = build_index()
        print(f"청크 {len(index['chunks'])}개를 {index_path()}에 저장하였다 (임베딩: {index['backend']}, {index['model']})")
    elif len(sys.argv) == 3 and sys.argv[1] == "eval":
        rate, hits, rows = recall_at_k(sys.argv[2], get_index())
        for hit, row in zip(hits, rows):
            print(f"[{'O' if hit else 'X'}] {row['질문']}")
        print(f"재현율(top-3): {sum(hits)}/{len(rows)} ({rate:.0%})")
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
