# 운영 기록 견본

이 폴더의 `access.log`, `error.log`, `llm.log`는 `jobprep`을 2027-09-06(월)부터 2027-09-12(일)까지 운영하였다고 가정하고 만든 **가상의 기록**이다. 「AI에이전트 기획 및 개발」 5장(MCP 서버가 읽는 운영 기록)과 12장(관측과 비용)에서 쓴다. 사용자를 식별할 수 있는 정보(IP 주소, 계정, 질문 원문)는 넣지 않았다.

## 형식

한 줄이 사건 하나이다. 앞의 네 칸은 날짜, 시각, 수준, 기록기 이름이고, 나머지는 `이름=값` 쌍이다. 값에 빈칸이 있으면 큰따옴표로 감싼다.

```
2027-09-06 09:05:07 INFO jobprep.access method=GET path=/api/jobs status=200 ms=24
2027-09-08 14:03:47 ERROR jobprep.api path=/api/summary status=503 error=LLMError detail="LLM 호출에 실패하였다: RateLimitError"
2027-09-06 09:06:51 INFO jobprep.llm task=summary model=claude-haiku-5-5 input_tokens=1056 output_tokens=286
```

| 파일 | 기록기 | 담는 것 |
|---|---|---|
| `access.log` | `jobprep.access` | 요청마다 방법(`method`), 경로(`path`), 상태 코드(`status`), 처리 시간(`ms`, 밀리초) |
| `error.log` | `jobprep.api`, `jobprep.llm` | 경고(WARNING)와 오류(ERROR). API 오류는 `status`, `error`(예외 이름), `detail`을 담는다 |
| `llm.log` | `jobprep.llm` | LLM 호출마다 기능(`task`), 모델(`model`), 입력·출력 토큰 수. 실패하면 `error` |

서버를 띄울 때 환경 변수 `LOG_DIR`을 정하면(예: `LOG_DIR=logs/runtime`) 같은 형식의 기록이 그 폴더에 쌓인다. `logs/runtime/`은 `.gitignore`에 있다.

## 견본에 들어 있는 사건

견본에는 운영 중에 볼 수 있는 사건 몇 가지가 들어 있다. 무엇이 언제 일어났는지는 기록을 읽어 찾는다. 기록을 분석하는 실습의 답이 되므로 이 문서에는 적지 않는다.
