# -*- coding: utf-8 -*-
"""문서 읽기와 청킹. (완성되어 있음. 설정은 환경 변수로 바꾼다)

청크 하나는 다음 키를 가진 사전이다.
    id        "문서이름#번호"
    source    문서 파일 이름(확장자 제외). 예: 현장실습_운영규정
    title     문서의 첫 줄 제목(# 줄)
    heading   청크가 시작하는 절의 제목(## 줄). 머리말은 "머리말"
    sections  청크가 걸쳐 있는 절 제목 목록(재현율 계산에 쓴다)
    text      청크 본문(화면과 프롬프트에 나가는 글)
    embed_text 임베딩에 넣는 글(제목 붙이기가 켜져 있으면 「문서 제목 > 절 제목」이 앞에 붙는다)

자르는 방식(CHUNK_MODE)
    heading  ## 제목 단위로 자른다. 절이 CHUNK_MAX_CHARS보다 길면 문단 경계에서 다시 나눈다.
    size     제목과 상관없이 CHUNK_MAX_CHARS 글자씩 자르고, CHUNK_OVERLAP 글자를 겹친다.
"""
import re
from pathlib import Path

from . import config

PREAMBLE = "머리말"
MIN_SECTION_OVERLAP = 30  # 청크가 절과 이만큼 이상 겹쳐야 그 절을 담았다고 본다
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def clean_text(text):
    """색인 전에 숨은 내용을 걷어 낸다. (걷어 낸 글, 걷어 낸 개수)를 돌려준다.

    마크다운의 HTML 주석(<!-- -->)은 화면에 보이지 않지만 그대로 색인하면 LLM에게는 보인다.
    사람이 검토하지 못한 글이 근거로 들어가는 통로이므로 색인 단계에서 지운다.
    """
    removed = len(_COMMENT.findall(text))
    return _COMMENT.sub("", text), removed


def load_documents(folder):
    """폴더의 .md 문서를 읽는다. 이름 순서로 돌려준다."""
    docs = []
    for path in sorted(Path(folder).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        text, removed = clean_text(raw)
        title = next((line[2:].strip() for line in text.splitlines() if line.startswith("# ")), path.stem)
        docs.append({"source": path.stem, "title": title, "text": text, "removed_comments": removed})
    return docs


def find_sections(text):
    """(절 제목, 시작 위치, 끝 위치) 목록. 첫 ## 앞은 머리말이다."""
    starts = [(m.start(), m.group(1).strip()) for m in re.finditer(r"^## (.+)$", text, re.MULTILINE)]
    sections = []
    first = starts[0][0] if starts else len(text)
    if text[:first].strip():
        sections.append((PREAMBLE, 0, first))
    for i, (pos, heading) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        sections.append((heading, pos, end))
    return sections


def _split_long(text, start, max_chars, overlap):
    """긴 글을 문단 경계에서 max_chars 이하 조각으로 나눈다. (조각, 시작 위치) 목록."""
    pieces = []
    # 빈 줄로 나뉜 문단을 (시작 위치, 문단) 목록으로 만든다
    paragraphs = [(m.start() + start, m.group(0).strip()) for m in re.finditer(r"(?:[^\n]*\S[^\n]*\n?)+", text)]
    buf, buf_start = "", None
    for pos, para in paragraphs:
        if buf and len(buf) + 2 + len(para) > max_chars:
            pieces.append((buf, buf_start))
            buf, buf_start = "", None
        if len(para) > max_chars:  # 한 문단이 상한보다 길면 글자 수로 자른다
            step = max(1, max_chars - overlap)
            for i in range(0, len(para), step):
                pieces.append((para[i:i + max_chars], pos + i))
            continue
        if buf_start is None:
            buf_start = pos
            buf = para
        else:
            buf = buf + "\n\n" + para
    if buf:
        pieces.append((buf, buf_start))
    return pieces


def _sections_in(span_start, span_end, sections):
    names = []
    for heading, s, e in sections:
        overlap = min(span_end, e) - max(span_start, s)
        # 짧은 절은 절반, 짧은 청크는 청크 전체가 겹치면 담은 것으로 본다
        if overlap > 0 and overlap >= min(MIN_SECTION_OVERLAP, (e - s) // 2, span_end - span_start):
            names.append(heading)
    return names


def chunk_document(doc, mode=None, max_chars=None, overlap=None, add_title=None):
    mode = mode or config.chunk_mode()
    max_chars = max_chars or config.chunk_max_chars()
    overlap = config.chunk_overlap() if overlap is None else overlap
    add_title = config.chunk_add_title() if add_title is None else add_title
    text = doc["text"]
    sections = find_sections(text)
    spans = []
    if mode == "heading":
        for heading, s, e in sections:
            body = text[s:e].strip()
            if not body:
                continue
            if len(body) <= max_chars:
                spans.append((body, s + text[s:e].index(body[0])))
            else:
                spans.extend(_split_long(text[s:e], s, max_chars, overlap))
    elif mode == "size":
        step = max(1, max_chars - overlap)
        for i in range(0, len(text), step):
            piece = text[i:i + max_chars]
            if piece.strip():
                spans.append((piece, i))
            if i + max_chars >= len(text):
                break
    else:
        raise ValueError("CHUNK_MODE는 heading 또는 size이다")

    chunks = []
    for n, (piece, start) in enumerate(spans, 1):
        names = _sections_in(start, start + len(piece), sections) or [sections[0][0] if sections else PREAMBLE]
        heading = names[0]
        prefix = f"[{doc['title']} > {heading}]\n" if add_title else ""
        chunks.append({
            "id": f"{doc['source']}#{n}",
            "source": doc["source"],
            "title": doc["title"],
            "heading": heading,
            "sections": names,
            "text": piece.strip(),
            "embed_text": prefix + piece.strip(),
        })
    return chunks


def chunk_all(docs, **kwargs):
    chunks = []
    for doc in docs:
        chunks.extend(chunk_document(doc, **kwargs))
    return chunks


def settings():
    return {
        "CHUNK_MODE": config.chunk_mode(),
        "CHUNK_MAX_CHARS": config.chunk_max_chars(),
        "CHUNK_OVERLAP": config.chunk_overlap(),
        "CHUNK_ADD_TITLE": int(config.chunk_add_title()),
    }
