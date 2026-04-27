"""Allow `python -m evaluation` to run the benchmark suite."""

from evaluation.runner import main


if __name__ == "__main__":
    raise SystemExit(main())

