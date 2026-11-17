#!/usr/bin/env bash
# 마크다운 파일 안의 주소를 모두 뽑아 HTTP 상태 코드를 찍는다.
# 사용법: bash ~/kits/Service_04장/도구/링크점검.sh ch04/시장조사.md [다른 파일 ...]
# 200은 "주소가 열린다"는 뜻일 뿐이다. 수치가 그 안에 있는지는 사람이 원문을 열어 확인한다.
# 000은 서버에 닿지 못했다는 뜻이다(주소 오류, 접속 차단, 시간 초과).
if [ $# -eq 0 ]; then
  echo "사용법: bash 링크점검.sh <파일> [파일 ...]"
  exit 1
fi
grep -ohE 'https?://[^ )>|`"]+' "$@" | sort -u | while read -r url; do
  code=$(curl -s -o /dev/null -L --max-time 15 -A "Mozilla/5.0 (course link check)" -w '%{http_code}' "$url")
  echo "$code $url"
done
