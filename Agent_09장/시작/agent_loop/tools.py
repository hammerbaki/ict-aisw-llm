"""에이전트 루프가 쓰는 도구.

도구 하나는 세 부분으로 이루어진다.
- 정의(definition): 모델에게 보내는 이름, 설명, 입력 스키마. 모델은 이것만 보고 부를지 정한다.
- 처리 함수(handler): 모델이 요청하면 이 프로그램이 실제로 실행하는 함수. 모델은 이 코드를 보지 못한다.
- 승인 필요 여부(needs_approval): 실행 전에 사람의 승인을 받아야 하는가.

모델이 만든 인자는 믿지 않는 입력으로 다룬다. run_tool()은 스키마 검사 → 처리 함수 안의 검사
(범위, 경로) → 실행 순서로 진행하고, 실패하면 예외로 멈추지 않고 오류 문장을 돌려준다.
그 문장은 루프가 tool_result의 is_error와 함께 모델에게 보낸다.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from api import jobs

REPO_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_DIR / "data" / "자료"
NOTES_DIR = Path(__file__).resolve().parent / "notes"
MAX_DOC_CHARS = 2000  # read_doc이 한 번에 돌려주는 최대 글자 수. 결과가 대화 기록에 쌓이기 때문이다

FIELDS = ["웹 개발", "백엔드 개발", "데이터 분석", "AI 서비스", "클라우드·인프라",
          "임베디드", "소프트웨어 테스트", "정보보안", "기술 지원"]


class ToolError(Exception):
    """도구가 요청을 처리할 수 없을 때 낸다. 메시지는 그대로 모델에게 간다."""


@dataclass
class Tool:
    definition: dict
    handler: object
    needs_approval: bool = False

    @property
    def name(self):
        return self.definition["name"]


@dataclass
class ToolOutcome:
    content: str
    is_error: bool = False


# ---------------------------------------------------------------------------
# 입력 검사: input_schema의 일부(type, required, additionalProperties, enum,
# minLength, maxLength, minimum, maximum)만 다루는 작은 검사기
# ---------------------------------------------------------------------------

_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "object": dict}


def _type_ok(value, type_name):
    if type_name in ("integer", "number") and isinstance(value, bool):
        return False  # 파이썬에서 True는 int이기도 하다
    return isinstance(value, _TYPES[type_name])


def validate(schema, args):
    """args가 schema에 맞는지 검사하고, 어긋난 점을 문장의 목록으로 돌려준다(맞으면 빈 목록)."""
    if not isinstance(args, dict):
        return ["입력은 JSON 객체여야 한다."]
    errors = []
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in args:
            errors.append(f"필수 인자 '{key}'가 없다.")
    if schema.get("additionalProperties") is False:
        for key in args:
            if key not in properties:
                errors.append(f"알 수 없는 인자 '{key}'이다. 쓸 수 있는 인자: {', '.join(properties)}.")
    for key, value in args.items():
        rule = properties.get(key)
        if rule is None:
            continue
        if "type" in rule and not _type_ok(value, rule["type"]):
            errors.append(f"'{key}'는 {rule['type']} 형식이어야 한다. 받은 값: {value!r}.")
            continue
        if "enum" in rule and value not in rule["enum"]:
            errors.append(f"'{key}'는 다음 중 하나여야 한다: {', '.join(map(str, rule['enum']))}. 받은 값: {value!r}.")
        if isinstance(value, str):
            if len(value) < rule.get("minLength", 0):
                errors.append(f"'{key}'가 비었거나 너무 짧다.")
            if "maxLength" in rule and len(value) > rule["maxLength"]:
                errors.append(f"'{key}'는 {rule['maxLength']}자 이하여야 한다.")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in rule and value < rule["minimum"]:
                errors.append(f"'{key}'는 {rule['minimum']} 이상이어야 한다. 받은 값: {value}.")
            if "maximum" in rule and value > rule["maximum"]:
                errors.append(f"'{key}'는 {rule['maximum']} 이하여야 한다. 받은 값: {value}.")
    return errors


# ---------------------------------------------------------------------------
# 도구 1: search_jobs (기준 저장소의 jobs.list_jobs()를 그대로 쓴다)
# ---------------------------------------------------------------------------

SEARCH_JOBS = {
    "name": "search_jobs",
    # TODO 3(7절 3단계): 모델이 이 도구를 언제 쓰고 언제 쓰지 않을지 판단할 수 있게 설명을 쓴다.
    #   무엇을 하는가, 무엇을 돌려주고 무엇을 돌려주지 않는가, 언제 쓰는가,
    #   언제 쓰지 않는가(그때는 read_doc), 결과가 0건이면 어떻게 하는가. 세 문장 이상.
    "description": "",
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {"type": "string", "enum": FIELDS,
                      "description": "직무 분야. 생략하면 모든 분야에서 찾는다."},
            "keyword": {"type": "string", "minLength": 1, "maxLength": 30,
                        "description": "제목, 기업명, 본문에 들어 있어야 하는 낱말 하나. 예: 파이썬"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 10,
                      "description": "돌려줄 최대 건수. 생략하면 5건이다."},
        },
        "required": [],
        "additionalProperties": False,
    },
}


def search_jobs(args):
    found = jobs.list_jobs(field=args.get("field"), q=args.get("keyword"))
    limit = args.get("limit", 5)
    keep = ["id", "title", "company", "field", "deadline", "days_left"]
    items = [{key: job[key] for key in keep} for job in found[:limit]]
    return json.dumps({"total": len(found), "returned": len(items), "jobs": items}, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 도구 2: read_doc (자료 폴더 안의 문서만 읽는다)
# ---------------------------------------------------------------------------

def doc_names():
    return sorted(path.name for path in DOCS_DIR.glob("*.md"))


READ_DOC = {
    "name": "read_doc",
    "description": (
        "학과 취업 자료(data/자료/ 폴더의 마크다운 문서 6편) 가운데 하나를 읽어 본문을 돌려준다. "
        "name에는 문서의 파일 이름만 쓴다. 폴더 경로, 절대 경로, '..'가 들어간 이름은 거부된다. "
        f"본문이 {MAX_DOC_CHARS}자를 넘으면 앞부분만 돌려주고 잘렸다고 표시한다. "
        "현장실습, 취업지원센터, 이력서와 자기소개서, 포트폴리오, 자격증 응시료 지원, 학과 추천 채용에 관한 질문에 쓴다. "
        "읽을 수 있는 문서: " + ", ".join(doc_names())
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "minLength": 1, "maxLength": 60,
                     "description": "문서 파일 이름. 예: 01_현장실습_안내.md"},
        },
        "required": ["name"],
        "additionalProperties": False,
    },
}


def read_doc(args):
    name = args["name"]
    # TODO 4(7절 4단계): 경로 검사 두 겹을 넣는다. 지금은 name을 그대로 경로에 붙인다.
    #   1차 검사(이름의 모양): name에 "/", "\\", "..", ":"가 있으면 ToolError("거부: ...")를 낸다.
    #   2차 검사(실제 경로): (DOCS_DIR / name).resolve()가 DOCS_DIR.resolve() 안에 있지 않으면
    #   ToolError("거부: ...")를 낸다. 오류 문장에는 읽을 수 있는 문서 목록(doc_names())을 넣는다.
    path = DOCS_DIR / name
    if path.suffix != ".md" or not path.is_file():
        raise ToolError(f"'{name}' 문서가 없다. 읽을 수 있는 문서: {', '.join(doc_names())}")
    text = path.read_text(encoding="utf-8")
    if len(text) > MAX_DOC_CHARS:
        return text[:MAX_DOC_CHARS] + f"\n…(잘림: 전체 {len(text)}자 가운데 앞 {MAX_DOC_CHARS}자)"
    return text


# ---------------------------------------------------------------------------
# 도구 3(확장, 7절): save_note. 파일을 쓰므로 사람의 승인이 필요하다
# ---------------------------------------------------------------------------

SAVE_NOTE = {
    "name": "save_note",
    "description": (
        "상담 내용을 agent_loop/notes/ 폴더에 마크다운 메모로 저장한다. "
        "사용자가 메모나 저장을 명시적으로 요청했을 때만 쓴다. "
        "같은 이름의 메모가 있으면 덮어쓰지 않고 오류를 돌려준다. 실행 전에 사람의 승인을 받는다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "minLength": 1, "maxLength": 40,
                      "description": "메모 파일 이름으로 쓸 제목. 한글, 영문, 숫자, 밑줄만 쓴다."},
            "body": {"type": "string", "minLength": 1, "maxLength": 2000, "description": "메모 본문"},
        },
        "required": ["title", "body"],
        "additionalProperties": False,
    },
}


def save_note(args):
    title = args["title"]
    if not all(ch.isalnum() or ch == "_" for ch in title):
        raise ToolError("title에는 한글, 영문, 숫자, 밑줄만 쓴다.")
    NOTES_DIR.mkdir(exist_ok=True)
    path = NOTES_DIR / f"{title}.md"
    if path.exists():
        raise ToolError(f"'{path.name}' 메모가 이미 있다. 다른 제목을 쓴다.")
    path.write_text(args["body"] + "\n", encoding="utf-8", newline="\n")
    return f"저장하였다: agent_loop/notes/{path.name} ({len(args['body'])}자)"


# ---------------------------------------------------------------------------
# 도구 묶음과 실행
# ---------------------------------------------------------------------------

def default_tools():
    """중심 실습의 도구 두 개."""
    return {
        "search_jobs": Tool(SEARCH_JOBS, search_jobs),
        "read_doc": Tool(READ_DOC, read_doc),
    }


def extended_tools():
    """7절: 승인이 필요한 도구를 더한 묶음."""
    tools = default_tools()
    tools["save_note"] = Tool(SAVE_NOTE, save_note, needs_approval=True)
    return tools


def definitions(tools):
    """API의 tools 매개변수로 보낼 정의의 목록."""
    return [tool.definition for tool in tools.values()]


def run_tool(name, args, tools):
    """도구 하나를 실행하고 ToolOutcome을 돌려준다. 어떤 경우에도 예외를 밖으로 내지 않는다."""
    tool = tools.get(name)
    if tool is None:
        return ToolOutcome(f"알 수 없는 도구 '{name}'이다. 쓸 수 있는 도구: {', '.join(tools)}", True)
    errors = validate(tool.definition["input_schema"], args)
    if errors:
        return ToolOutcome("입력 오류: " + " ".join(errors), True)
    try:
        return ToolOutcome(tool.handler(args))
    except ToolError as error:
        return ToolOutcome(str(error), True)
    except Exception as error:  # 예상하지 못한 오류도 루프를 멈추지 않는다. 내부 내용은 모델에게 보내지 않는다
        return ToolOutcome(f"도구 실행 중 오류가 났다({type(error).__name__}). 다른 방법을 쓰거나 사용자에게 알린다.", True)
