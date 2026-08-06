from __future__ import annotations

from datetime import UTC, datetime
import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """Xay dung flow corruption -> evaluate -> repair -> compare."""
    print("=== STARTING CORRUPTION & REPAIR PIPELINE FLOW ===")
    settings = load_settings()

    # 1. Load baseline clean dataset & metrics
    print(f"Loading clean baseline dataset from {settings.paths.clean_csv}...")
    # Keep optional empty text fields as strings so Chroma metadata remains
    # scalar and regenerated JSON artifacts do not contain unexpected nulls.
    df_clean = pd.read_csv(settings.paths.clean_csv, keep_default_na=False)
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    # 2. Corrupt data
    print("Simulating data corruption...")
    settings.paths.corruption_log.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted = corrupt_clean_dataframe(df_clean, settings.paths.corruption_log)
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_corrupted.to_csv(settings.paths.corrupted_clean_csv, index=False)
    df_corrupted.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2)

    # 3. Build corrupted Chroma index
    print("Building corrupted vector index...")
    index_corrupted = LocalEmbeddingIndex.build(
        df=df_corrupted,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )

    # 4. Evaluate corrupted pipeline
    print("Evaluating corrupted pipeline on frozen test set...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=index_corrupted,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )

    # 5. Quality & Freshness checks on corrupted data
    print("Running Quality & Freshness checks on corrupted data...")
    corrupted_quality = run_data_quality_checks(df_corrupted, settings, report_name="corrupted")
    corrupted_freshness = build_freshness_report(
        df_corrupted, settings, settings.paths.quality_dir / "freshness_corrupted.json"
    )

    # 6. Repair data from raw records
    print("Repairing data from raw source records...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    df_repaired = build_clean_dataframe(raw_records, datetime.now(UTC))
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    df_repaired.to_csv(settings.paths.repaired_clean_csv, index=False)
    df_repaired.to_json(settings.paths.repaired_clean_json, orient="records", indent=2)

    # 7. Build repaired Chroma index
    print("Building repaired vector index...")
    index_repaired = LocalEmbeddingIndex.build(
        df=df_repaired,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )

    # 8. Evaluate repaired pipeline
    print("Evaluating repaired pipeline on frozen test set...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=index_repaired,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )

    # 9. Quality & Freshness checks on repaired data
    print("Running Quality & Freshness checks on repaired data...")
    repaired_quality = run_data_quality_checks(df_repaired, settings, report_name="repaired")
    repaired_freshness = build_freshness_report(
        df_repaired, settings, settings.paths.quality_dir / "freshness_repaired.json"
    )

    # 10. Generate comparison report
    print("Generating Comparison Report (Baseline vs Corrupted vs Repaired)...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )

    print("=== CORRUPTION & REPAIR PIPELINE FLOW COMPLETED SUCCESSFULLY ===")
