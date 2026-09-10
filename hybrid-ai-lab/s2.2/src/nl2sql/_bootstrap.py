"""직접 파일 실행 시에도 저장소 패키지를 찾도록 경로 설정."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
