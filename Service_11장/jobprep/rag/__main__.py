# -*- coding: utf-8 -*-
"""취업 자료 질의응답(RAG) 명령. jobprep/ 폴더에서 실행한다.

    python -m rag index                      자료/의 문서를 청킹하고 임베딩해 rag/index/에 저장
    python -m rag search "질문" [--method vector|keyword|hybrid] [--k 3]
    python -m rag prompt "질문"              LLM에 보낼 증강 프롬프트를 보기만 한다(호출하지 않음)
    python -m rag ask "질문"                 검색 → 증강 → 생성
    python -m rag chat                       대화형(빈 줄을 넣으면 끝)
    python -m rag eval [--method ...] [--k 3] [--md] [--csv 파일]
    python -m rag calibrate                  기준값을 정하기 위한 유사도 비교

환경 변수: EMBED_BACKEND(fallback 기본|ollama|auto), EMBED_MODEL, CHUNK_MODE, CHUNK_MAX_CHARS,
CHUNK_OVERLAP, CHUNK_ADD_TITLE, TOP_K, SEARCH_METHOD, RAG_MIN_SCORE, MAX_TURNS, LLM_FAKE, LLM_MODEL
"""
import argparse
import sys

from . import answer as answer_mod
from . import chunker, config, evaluate, search, store

try:  # 10장처럼 jobprep/.env가 있으면 읽는다(LLM_FAKE, LLM_MODEL, ANTHROPIC_API_KEY). 이미 설정된 값은 덮어쓰지 않는다
    from dotenv import load_dotenv
    load_dotenv(config.ROOT / ".env")
except ImportError:
    pass


def _print_hits(hits):
    for h in hits:
        c = h["chunk"]
        print(f'{h["rank"]}. [점수 {h["score"]:.4f} | 유사도 {h["similarity"]:.4f}] {c["source"]} > {c["heading"]}')
        body = " ".join(c["text"].split())
        print(f"   {body[:90]}…")


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    p = argparse.ArgumentParser(prog="python -m rag", description="취업 자료 질의응답(RAG)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index")
    for name in ("search", "prompt", "ask"):
        s = sub.add_parser(name)
        s.add_argument("question")
        s.add_argument("--method", default=None)
        s.add_argument("--k", type=int, default=None)
    sub.add_parser("chat")
    e = sub.add_parser("eval")
    e.add_argument("--method", default=None)
    e.add_argument("--k", type=int, default=None)
    e.add_argument("--csv", default=str(evaluate.DEFAULT_CSV))
    e.add_argument("--md", action="store_true", help="마크다운 표로 출력")
    c = sub.add_parser("calibrate")
    c.add_argument("--method", default=None)
    args = p.parse_args(argv)

    if args.cmd == "index":
        idx = store.build_index()
        m = idx.meta
        print(f'문서 {len(m["docs"])}개, 청크 {m["chunks"]}개, 차원 {m["dim"]}, 임베딩 {m["backend"]}/{m["model"]}')
        print("청킹 설정: " + ", ".join(f"{k}={v}" for k, v in chunker.settings().items()))
        if m["removed_comments"]:
            print(f'숨은 주석 {m["removed_comments"]}개를 걷어 냈다')
        print(f"저장: {config.index_dir()}")
        return
    idx = store.load_index()
    if args.cmd == "search":
        _print_hits(search.search(args.question, idx, k=args.k, method=args.method))
    elif args.cmd == "prompt":
        hits = answer_mod.fit_evidence(search.search(args.question, idx, k=args.k, method=args.method))
        print(answer_mod.build_prompt(args.question, hits))
    elif args.cmd == "ask":
        result = answer_mod.answer(args.question, idx, k=args.k, method=args.method)
        print(result["answer"])
        print(f'\n(1위 유사도 {result["top_score"]:.4f}, 근거 사용: {result["grounded"]})')
        for cit in result["citations"]:
            mark = "*" if cit["cited"] else " "
            print(f'{mark}[{cit["n"]}] {cit["title"]} > {cit["heading"]} (유사도 {cit["score"]:.4f})')
    elif args.cmd == "chat":
        history = []
        while True:
            try:
                q = input("질문> ").strip()
            except EOFError:
                q = ""
            if not q:
                break
            result = answer_mod.answer(q, idx, history=history)
            print(result["answer"] + "\n")
            # 이력에는 원래 질문과 답만 남긴다. 증강 프롬프트(근거 블록)는 넣지 않는다.
            history += [{"role": "user", "content": q}, {"role": "assistant", "content": result["answer"]}]
    elif args.cmd == "eval":
        k = args.k or config.top_k()
        method = args.method or config.search_method()
        rows = evaluate.run_eval(idx, args.csv, k=k, method=method)
        settings = {key: idx.meta[key] for key in ("CHUNK_MODE", "CHUNK_MAX_CHARS", "CHUNK_OVERLAP", "CHUNK_ADD_TITLE")}
        settings["임베딩"] = f'{idx.meta["backend"]}/{idx.meta["model"]}'
        settings["청크"] = idx.meta["chunks"]
        print(evaluate.report(rows, k, method, settings, as_markdown=args.md))
    elif args.cmd == "calibrate":
        print(evaluate.calibrate(idx, method=args.method))


if __name__ == "__main__":
    main()
