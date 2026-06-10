from __future__ import annotations

from app.core import settings
from app.pipeline.aggregate import AggregateRunner


def main() -> None:
    runner = AggregateRunner(settings.data_dir)
    result = runner.run_once()
    print(result.model_dump())


if __name__ == "__main__":
    main()
