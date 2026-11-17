import sys
from pathlib import Path

# 도구 폴더(이 파일의 한 단계 위)를 가져오기 경로에 넣는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
