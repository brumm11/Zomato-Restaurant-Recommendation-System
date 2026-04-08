from backend.phases.phase2.data.pipeline import run_ingestion


def main() -> None:
    report = run_ingestion()
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
