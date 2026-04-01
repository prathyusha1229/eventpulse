from __future__ import annotations

from app.core import settings
from app.pipeline.extract_clean import ExtractCleanRunner


def main() -> None:
    runner = ExtractCleanRunner(settings.data_dir)
    result = runner.run_once()
    print(result.model_dump())


if __name__ == "__main__":
    main()