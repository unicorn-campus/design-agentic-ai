from __future__ import annotations

import json
from pathlib import Path

from help_desk_dataset.quality import measure_quality, render_quality_report
from help_desk_dataset.seed import generate_all_seed_files
from help_desk_runtime.settings import RuntimeSettings


SERVICE_ROOT = Path(__file__).resolve().parents[1]
COMMON_ENV = SERVICE_ROOT.parents[1] / "common" / ".env.example"


def main() -> None:
    settings = RuntimeSettings(_env_file=COMMON_ENV)
    seed_dir = SERVICE_ROOT / "config" / "mock_responses"
    created = generate_all_seed_files(settings, seed_dir)
    results = []
    for stage_id, path in created.items():
        payload = json.loads(path.read_text(encoding="utf-8"))
        results.append(measure_quality(stage_id, payload["rows"]))
    report_dir = SERVICE_ROOT / "config" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "source_quality.md").write_text(
        render_quality_report(results),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
