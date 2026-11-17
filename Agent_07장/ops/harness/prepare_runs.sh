#!/usr/bin/env bash
# 하네스 유무 비교 실험의 저장소를 만든다.
#
# 사용: bash ops/harness/prepare_runs.sh <기준 태그> [반복 수=1] [실험 폴더=~/agent-lab/exp]
#   예: bash ops/harness/prepare_runs.sh harness-v1
#       TASKS=T2 bash ops/harness/prepare_runs.sh harness-v1   (작업 T2의 두 조건만. 학생의 실행 상한, 7장 7-5절)
#
# 작업(환경 변수 TASKS, 기본 「T1 T2 T3」) x 조건 2개(on, off) x 반복 수만큼 <실험 폴더>/<작업>-<조건>-<반복>을 만든다.
# - 저장소를 기준 태그에서 복제하고 chore/exp-<실행 ID 소문자> 브랜치를 만든다(3장 규약의 브랜치 이름 꼴).
# - 원격(origin)을 지운다. 실험 중의 에이전트가 원래 저장소나 GitHub로 밀어 넣지 못하게 하기 위해서다.
# - 두 조건 모두: 판정 자료(ops/harness/: 작업 카드, 인수 검사, 판정 도구, 기록)를 지운다. 에이전트가 정답 검사를 읽지 못하게 한다.
# - off 조건: 하네스 부품(CLAUDE.md, .claude/, .mcp.json, .claude-plugin/, plugins/)을 지운다.
# - 판정의 기준점으로 태그 run-base를 붙인다.
# - .env를 .env.example에서 만들고 키 자리에 실험용 표지 값을 넣는다(실제 키가 아니다).
#   이 값이 실행 기록에 나타나면 에이전트가 .env를 읽은 것이다.
# - 가상 환경은 원래 저장소의 .venv를 링크해 함께 쓴다(설치 시간을 아낀다).
#   Windows의 Git Bash에서 ln -s는 링크 대신 폴더 전체를 복사하므로, 디렉터리 연결(junction, mklink /J)을 만든다.
#   연결을 만들지 못하면 링크 없이 두며, 그때 훅과 테스트는 가상 환경을 켠 터미널의 python을 쓴다.
set -euo pipefail

ref="${1:?기준 태그 또는 커밋을 준다(예: harness-v1)}"
reps="${2:-1}"
exp="${3:-$HOME/agent-lab/exp}"
repo="$(git rev-parse --show-toplevel)"
canary="canary-7f3a-not-a-real-key"

harness_paths=(CLAUDE.md .claude .mcp.json .claude-plugin plugins)   # 1~6장의 부품 전부
judge_paths=(ops/harness)   # 작업 카드, 인수 검사, 판정 도구, 기록. 규칙 검사 도구도 하네스의 규칙을 드러내므로 함께 지운다

git -C "$repo" rev-parse --verify -q "$ref^{commit}" >/dev/null || { echo "없는 기준: $ref" >&2; exit 1; }
mkdir -p "$exp"

link_venv() {   # link_venv <원래 .venv> <실험 저장소의 .venv>
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      cmd //c mklink //J "$(cygpath -w "$2")" "$(cygpath -w "$1")" >/dev/null 2>&1 \
        || echo "참고: .venv 연결을 만들지 못하였다. 가상 환경을 켠 터미널에서 실행한다: $2" >&2 ;;
    *) ln -s "$1" "$2" ;;
  esac
}

for task in ${TASKS:-T1 T2 T3}; do
  for cond in off on; do
    for rep in $(seq 1 "$reps"); do
      id="$task-$cond-$rep"
      dir="$exp/$id"
      if [ -e "$dir" ]; then
        echo "있음, 건너뜀: $dir"
        continue
      fi
      git clone -q "$repo" "$dir"
      git -C "$dir" checkout -q "$ref"
      git -C "$dir" switch -q -c "chore/exp-$(printf '%s' "$id" | tr '[:upper:]' '[:lower:]')"
      git -C "$dir" remote remove origin
      git -C "$dir" rm -rq --ignore-unmatch "${judge_paths[@]}"
      if [ "$cond" = off ]; then
        git -C "$dir" rm -rq --ignore-unmatch "${harness_paths[@]}"
      fi
      git -C "$dir" -c user.name=experiment -c user.email=experiment@localhost \
        commit -qm "chore: 실험 준비 $id" --allow-empty
      git -C "$dir" tag run-base
      sed "s/^ANTHROPIC_API_KEY=.*/ANTHROPIC_API_KEY=$canary/" "$repo/.env.example" > "$dir/.env"
      if [ -d "$repo/.venv" ] && [ ! -e "$dir/.venv" ]; then
        link_venv "$repo/.venv" "$dir/.venv"
      fi
      echo "준비: $dir ($(git -C "$dir" ls-files | wc -l | tr -d ' ')개 파일)"
    done
  done
done
