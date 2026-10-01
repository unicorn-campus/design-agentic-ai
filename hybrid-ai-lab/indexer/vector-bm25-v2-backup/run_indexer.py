"""명령행 인덱서를 실행하고 응용 결과의 종료 코드를 운영체제에 전달함."""

from app.presentation.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
