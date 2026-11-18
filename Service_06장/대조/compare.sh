#!/bin/bash
# 원본(python -m json.tool)과 재구현(python jsonfmt.py)에 같은 인자를 주고
# 표준 출력과 종료 코드를 견준다. 표준 오류는 견주지 않는다(6장 5-3).
#
# 쓰는 법: 재구현 폴더에서  bash compare.sh  [경우 파일, 기본 cases.txt]
# 경우 파일: 한 줄에 인자 한 벌. 빈 줄과 # 으로 시작하는 줄은 건너뛴다.
# 「< a.json --sort-keys」처럼 < 와 파일 이름으로 시작하면 그 파일을 표준 입력으로 준다.
# 재구현 파일의 이름이 jsonfmt.py가 아니면  IMPL=다른이름.py bash compare.sh
# 줄 끝의 \r(Windows 편집기가 붙이는 CRLF)은 지우고 읽는다.

cases="${1:-cases.txt}"
impl="${IMPL:-jsonfmt.py}"

if [ ! -f "$cases" ]; then echo "경우 파일이 없다: $cases" >&2; exit 2; fi
if [ ! -f "$impl" ]; then echo "재구현 파일이 없다: $impl" >&2; exit 2; fi

same=0; diff=0
while IFS= read -r args || [ -n "$args" ]; do
  args="${args%$'\r'}"
  case "$args" in ''|'#'*) continue ;; esac
  # 「< 파일 인자…」 꼴이면 그 파일을 표준 입력으로 준다. 아니면 빈 입력을 준다.
  inp=/dev/null; shown="$args"
  if [ "${args:0:1}" = "<" ]; then
    rest="${args#<}"; rest="${rest# }"; inp="${rest%% *}"
    if [ "$rest" = "$inp" ]; then args=""; else args="${rest#* }"; fi
  fi
  # 인자를 일부러 따옴표 없이 넘긴다. 한 줄의 인자가 공백으로 나뉘어 들어간다.
  python -m json.tool $args > o.out 2> o.err < "$inp"; oc=$?
  python "$impl" $args > r.out 2> r.err < "$inp"; rc=$?
  args="$shown"
  if cmp -s o.out r.out && [ "$oc" -eq "$rc" ]; then
    res="같다"; same=$((same + 1))
  else
    res="다르다"; diff=$((diff + 1))
  fi
  echo "$res | 종료 코드 $oc, $rc | $args"
done < "$cases"
echo "합계: 같다 $same, 다르다 $diff (견준 것: 표준 출력, 종료 코드)"
