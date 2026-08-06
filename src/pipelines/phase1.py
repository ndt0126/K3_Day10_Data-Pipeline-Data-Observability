from __future__ import annotations

from datetime import UTC, datetime
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung baseline pipeline end-to-end cho Phase 1."""
    print("=== STARTING PHASE 1 BASELINE PIPELINE ===")
    settings = load_settings()

    # 1. Load hoac fetch raw records
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        print("Fetching raw records from Crossref source...")
        records = fetch_source_records(settings)
    else:
        print(f"Loading raw records from {settings.paths.raw_records_json}...")
        records = load_raw_records(settings.paths.raw_records_json)

    # 2. Clean data
    if settings.paths.clean_csv.exists() and not settings.refresh_source:
        print(f"Loading clean data from {settings.paths.clean_csv}...")
        df = pd.read_csv(settings.paths.clean_csv)
    else:
        print("Cleaning raw records...")
        df = build_clean_dataframe(records, datetime.now(UTC))
        settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(settings.paths.clean_csv, index=False)
        df.to_json(settings.paths.clean_json, orient="records", indent=2)

    # 3. Build Chroma index
    print("Building Chroma vector index...")
    index = LocalEmbeddingIndex.build(
        df=df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    # 4. Evaluation set
    if settings.paths.eval_testset.exists() and not settings.refresh_test_set:
        print(f"Loading evaluation test set from {settings.paths.eval_testset}...")
        test_set = read_json(settings.paths.eval_testset)
    else:
        print("Building evaluation test set...")
        test_set = build_test_set(df, settings.paths.eval_testset)

    # 5. Evaluate pipeline
    print("Evaluating baseline pipeline...")
    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )

    # 6. Quality checks va Freshness report
    print("Running Data Quality & Freshness checks...")
    quality = run_data_quality_checks(df, settings, report_name="baseline")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    # 7. Generate markdown report
    print("Generating Phase 1 Markdown report...")
    source_summary = {
        "source_api": settings.source_api,
        "raw_count": len(records),
        "clean_count": len(df),
        "eval_count": len(test_set),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=bundle.summary,
        quality=quality,
        freshness=freshness,
    )

    print("=== PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY ===")

