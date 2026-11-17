# 시작 파일 (jobprep/web/ 로 복사한다)

| 경로 | 내용 |
|---|---|
| `data/jobs.json` | 수업용 가상 채용 공고 30건. 기업명과 공고는 지어낸 것이다 |
| `css/tokens.css` | 8장 디자인 토큰(`docs/설계/디자인토큰.md` v1.0)을 8장의 `tokens_to_css.py`로 옮긴 것과, 9장 견본 구현이 쓰는 짧은 이름의 별칭 블록 |
| `check/` | 자동 검사 두 개와 안내 |

화면 파일(`index.html`, `detail.html`, `saved.html`, `schedule.html`), 화면 모양(`css/style.css`), 동작(`js/`)은
명세에서 Claude Code 로 구현한다. 시작 파일은 고치지 않고 쓴다. `tokens.css`를 바꿔야 하면 디자인토큰.md 를 먼저 고친다.
