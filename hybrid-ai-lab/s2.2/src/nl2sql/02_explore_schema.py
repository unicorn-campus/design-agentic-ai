"""완성 제공 실행 예제."""
try:
    from . import _bootstrap
except ImportError:
    import _bootstrap

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('schema'))
