# -*- coding: utf-8 -*-
"""색인의 저장과 읽기. (완성되어 있음)

작은 규모(청크 수천 개 이하)에서는 벡터 데이터베이스 없이 파일 세 개로 충분하다.
    index/chunks.json   청크 목록(본문과 메타데이터)
    index/vectors.npy   청크 벡터 행렬(청크 수 x 차원). 행 순서가 chunks.json과 같다
    index/meta.json     만든 날짜, 임베딩 경로와 모델, 청킹 설정
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np

from . import chunker, config, embedder


class Index:
    def __init__(self, chunks, vectors, meta):
        self.chunks = chunks
        self.vectors = vectors
        self.meta = meta

    def __len__(self):
        return len(self.chunks)


def build_index(docs_dir=None, index_dir=None):
    docs_dir = Path(docs_dir or config.docs_dir())
    index_dir = Path(index_dir or config.index_dir())
    docs = chunker.load_documents(docs_dir)
    if not docs:
        raise SystemExit(f"{docs_dir}에 .md 문서가 없다")
    chunks = chunker.chunk_all(docs)
    vectors = embedder.embed_texts([c["embed_text"] for c in chunks])
    meta = {
        "created": datetime.now().isoformat(timespec="seconds"),
        "docs": [d["source"] for d in docs],
        "removed_comments": sum(d["removed_comments"] for d in docs),
        "chunks": len(chunks),
        "dim": int(vectors.shape[1]),
        **embedder.describe(),
        **chunker.settings(),
    }
    index_dir.mkdir(parents=True, exist_ok=True)
    (index_dir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=1), encoding="utf-8")
    np.save(index_dir / "vectors.npy", vectors.astype(np.float32))
    (index_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return Index(chunks, vectors, meta)


def load_index(index_dir=None):
    index_dir = Path(index_dir or config.index_dir())
    if not (index_dir / "meta.json").exists():
        raise FileNotFoundError(f"색인이 없다: {index_dir}. 먼저 python -m rag index 를 실행한다")
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
    current = embedder.describe()
    if (meta["backend"], meta["model"]) != (current["backend"], current["model"]):
        raise RuntimeError(
            f"색인은 {meta['backend']}/{meta['model']}로 만들었는데 지금은 {current['backend']}/{current['model']}로 "
            "질문을 임베딩한다. 두 벡터는 비교할 수 없으므로 색인을 다시 만든다(python -m rag index)")
    chunks = json.loads((index_dir / "chunks.json").read_text(encoding="utf-8"))
    vectors = np.load(index_dir / "vectors.npy")
    return Index(chunks, vectors, meta)
