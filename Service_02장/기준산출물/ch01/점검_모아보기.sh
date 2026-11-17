#!/usr/bin/env bash
# 점검표의 명령을 한 번에 실행해 출력을 차례로 보인다. 판정은 하지 않는다.
# 1장 8-7절의 (다)에서, 13번 요구를 더해 다시 만든 프로그램이 1~12번을 여전히
# 지키는지(회귀) 한 화면으로 보는 데 쓴다. 판정 기호는 사람이 출력을 읽고 비교.md에 적는다.
# (나)의 첫 점검(8-5절)에서는 쓰지 않는다. 그때는 명령을 하나씩 직접 친다.
#
# 사용법 (ch01 폴더에서):
#   bash 점검_모아보기.sh 다_보강/dday.py
#   bash 점검_모아보기.sh 나_요구목록/dday.py
#   PY=python3 bash 점검_모아보기.sh 다_보강/dday.py   # 파이썬 명령 이름을 정할 때(macOS)
set -u
PROG="${1:?사용법: bash 점검_모아보기.sh <프로그램 경로>}"
if [ -z "${PY:-}" ]; then
  if command -v python >/dev/null 2>&1; then PY=python; else PY=python3; fi
fi
DATA="${DATA:-점검자료}"
TODAY="--today 2027-03-10"

show() { echo; echo "===== $1"; echo "\$ $2"; }

show "1·4·5·6·7 기본 자료" "$PY $PROG $DATA/공고_기본.csv $TODAY"
$PY "$PROG" "$DATA/공고_기본.csv" $TODAY; echo "(종료 코드 $?)"

show "2 기준일 2027-03-01" "$PY $PROG $DATA/공고_기본.csv --today 2027-03-01"
$PY "$PROG" "$DATA/공고_기본.csv" --today 2027-03-01; echo "(종료 코드 $?)"

show "3 엑셀 저장본" "$PY $PROG $DATA/공고_엑셀저장.csv $TODAY"
$PY "$PROG" "$DATA/공고_엑셀저장.csv" $TODAY; echo "(종료 코드 $?)"

show "8 날짜 오류" "$PY $PROG $DATA/공고_날짜오류.csv $TODAY"
$PY "$PROG" "$DATA/공고_날짜오류.csv" $TODAY; echo "(종료 코드 $?)"

show "9 없는 파일" "$PY $PROG $DATA/없는파일.csv $TODAY"
$PY "$PROG" "$DATA/없는파일.csv" $TODAY; echo "(종료 코드 $?)"

show "10 빈 목록" "$PY $PROG $DATA/공고_빈목록.csv $TODAY"
$PY "$PROG" "$DATA/공고_빈목록.csv" $TODAY; echo "(종료 코드 $?)"

show "11 파이썬 파일과 import 줄" "ls $(dirname "$PROG")/*.py; grep -n '^import\|^from' $PROG"
ls "$(dirname "$PROG")"/*.py
grep -n '^import\|^from' "$PROG"

show "12 stdout만 (경고가 사라져야 한다)" "$PY $PROG $DATA/공고_날짜오류.csv $TODAY 2>/dev/null"
$PY "$PROG" "$DATA/공고_날짜오류.csv" $TODAY 2>/dev/null

show "13 지난 공고만 있는 자료" "$PY $PROG $DATA/공고_모두지남.csv $TODAY"
$PY "$PROG" "$DATA/공고_모두지남.csv" $TODAY; echo "(종료 코드 $?)"
