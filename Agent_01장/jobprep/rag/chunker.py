"""문서를 검색 단위(청크)로 자른다."""


def chunk_markdown(text, source):
    """마크다운 문서를 '## ' 절 단위로 자른다.

    각 청크는 다음 키를 가진 dict이다.
    - id: "<파일 이름>#<순번>"
    - source: 파일 이름
    - title: "<문서 제목> > <절 제목>"
    - text: 문서 제목 줄, 절 제목 줄, 절 본문을 이은 글

    문서 제목('# ')을 모든 청크에 붙이는 까닭은 절 본문만으로는 어느 문서의
    내용인지 알 수 없는 경우가 있기 때문이다. 첫 '## ' 앞의 머리말은 청크로 만들지 않는다.
    """
    doc_title = source
    chunks = []
    section = None
    body = []

    def flush():
        if section is not None and "".join(body).strip():
            chunks.append({
                "id": f"{source}#{len(chunks) + 1}",
                "source": source,
                "title": f"{doc_title} > {section}",
                "text": f"# {doc_title}\n## {section}\n" + "\n".join(body).strip(),
            })

    for line in text.splitlines():
        if line.startswith("# "):
            doc_title = line[2:].strip()
        elif line.startswith("## "):
            flush()
            section = line[3:].strip()
            body = []
        elif section is not None:
            body.append(line)
    flush()
    return chunks
