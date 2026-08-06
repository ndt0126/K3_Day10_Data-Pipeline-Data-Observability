"""Run the evaluation metrics for one or more pipeline states.

Covers Duty 3 (thuc thi danh gia chi so). `evaluate_pipeline` in
`src/evaluation/metrics.py` does the scoring; this script's job is to feed it
the right index and the right output paths for each state, then sanity-check
what came back.

All states are scored against the same frozen `data/eval/test_set.json`. That
is what makes the three-way comparison meaningful.

Usage
-----
    uv run python script/check_llm.py                      # do this first
    uv run python script/run_evaluation.py                 # baseline
    uv run python script/run_evaluation.py --state corrupted
    uv run python script/run_evaluation.py --all
    uv run python script/run_evaluation.py --compare       # read existing metrics, no LLM calls
    uv run python script/run_evaluation.py --audit         # integrity check, no LLM calls
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

from _tv3_common import STATES, format_row, section, state_paths

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from retrieval.index import LocalEmbeddingIndex

EVAL_SET_FIELDS = ("id", "question_type", "question", "ground_truth", "ground_truth_doc_ids")
HEADLINE_METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
FALLBACK_MARKER = "Fallback heuristic judge"


def validate_test_set(path) -> list[str]:
    """Check test_set.json against the agreed Evaluation Set contract."""
    problems: list[str] = []
    if not path.exists():
        return [f"test set not found at {path}"]

    test_set = read_json(path)
    if not isinstance(test_set, list) or not test_set:
        return ["test set is not a non-empty JSON list"]

    for index, item in enumerate(test_set):
        missing = [field for field in EVAL_SET_FIELDS if field not in item]
        if missing:
            problems.append(f"sample {index} missing: {', '.join(missing)}")
        elif not isinstance(item["ground_truth_doc_ids"], list):
            problems.append(f"sample {index}: ground_truth_doc_ids must be a list")

    ids = [item.get("id") for item in test_set]
    if len(set(ids)) != len(ids):
        problems.append("duplicate sample ids")
    return problems


def run_state(settings, state: str) -> dict[str, Any] | None:
    target = state_paths(settings, state)
    print(f"\n{'=' * 72}\nEVALUATING: {state}\n{'=' * 72}")

    if not target.embeddings_json.exists():
        print(f"  SKIP  no index for '{state}' -- run check_retrieval.py --state {state} first")
        return None

    index = LocalEmbeddingIndex.load(settings, target.embeddings_json)
    print(format_row("collection", index.collection_name))
    print(format_row("documents", index.collection.count()))
    print(format_row("test set", settings.paths.eval_testset.name))
    print(format_row("RUN_RAGAS", os.getenv("RUN_RAGAS", "(unset -> ragas skipped)")))
    print("\n  scoring... (one LLM judge call per sample)")

    bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=target.metrics_json,
        answers_output_path=target.answers_json,
    )

    summary = bundle.summary
    print(section("Metrics"))
    for key in HEADLINE_METRICS:
        print(format_row(key, f"{summary[key]:.4f}"))
    print(format_row("samples", summary["samples"]))

    ragas = summary.get("ragas", {})
    if isinstance(ragas, dict) and "skipped" in ragas:
        print(format_row("ragas", "skipped (set RUN_RAGAS=1)"))
    elif isinstance(ragas, dict) and "error" in ragas:
        print(format_row("ragas", f"ERROR {ragas['error'][:60]}"))
    else:
        for key, value in (ragas or {}).items():
            print(format_row(f"ragas.{key}", value))

    # The judge swallows every exception and silently degrades to token-F1.
    # Without this check a dead API key still produces judge_accuracy numbers.
    fallbacks = sum(
        1 for item in bundle.answers if FALLBACK_MARKER in item["judge"].get("reasoning", "")
    )
    print(section("Judge integrity"))
    if fallbacks == 0:
        print(f"  OK  all {len(bundle.answers)} verdicts came from the LLM")
    elif fallbacks == len(bundle.answers):
        print(
            f"  FAIL  all {fallbacks} verdicts used the fallback heuristic.\n"
            "        The LLM judge never ran -- judge_accuracy and mean_judge_score are\n"
            "        not LLM metrics. Run script/check_llm.py before reporting these."
        )
    else:
        print(f"  WARN  {fallbacks}/{len(bundle.answers)} verdicts used the fallback heuristic (partial failures)")

    # Per-question-type breakdown -- shows which retrieval path degrades first.
    print(section("By question type"))
    by_type: dict[str, list[dict[str, Any]]] = {}
    for item in bundle.answers:
        by_type.setdefault(item["question_type"], []).append(item)
    for question_type, items in sorted(by_type.items()):
        hit = sum(1 for i in items if i["retrieval_hit"]) / len(items)
        f1 = sum(i["token_f1"] for i in items) / len(items)
        print(f"  {question_type:<12} n={len(items):<3} hit_rate={hit:.2f}  token_f1={f1:.4f}")

    print(f"\n  wrote {target.metrics_json.name} and {target.answers_json.name}")
    return summary


def audit(settings) -> int:
    """Check existing metrics/answers artifacts without spending a single token.

    Three questions this answers:
      1. Did the LLM judge actually run, or did every verdict come from the
         silent token-F1 fallback in `_judge_answer`?
      2. Do the numbers in *_metrics.json actually match the *_answers.json
         they claim to summarise? (report/artifact consistency)
      3. Which question types degrade, and by how much?
    """
    from statistics import mean

    print(f"\n{'=' * 72}\nAUDIT OF EXISTING ARTIFACTS (no LLM calls)\n{'=' * 72}")
    failures = 0

    for state in STATES:
        target = state_paths(settings, state)
        if not target.answers_json.exists():
            print(f"\n  {state}: no answers file, skipped")
            continue

        answers = read_json(target.answers_json)
        print(section(f"{state}  ({len(answers)} samples)"))

        # 1. judge integrity
        fallbacks = sum(
            1 for item in answers if FALLBACK_MARKER in item["judge"].get("reasoning", "")
        )
        if fallbacks == 0:
            print("  OK    judge: all verdicts came from the LLM")
        elif fallbacks == len(answers):
            print(
                f"  FAIL  judge: all {fallbacks} verdicts used the token-F1 fallback.\n"
                "        judge_accuracy and mean_judge_score are NOT LLM metrics here --\n"
                "        they are a step function of token_f1 and carry no extra signal."
            )
            failures += 1
        else:
            print(f"  WARN  judge: {fallbacks}/{len(answers)} verdicts used the fallback")

        # 2. do the stored metrics match the stored answers?
        if target.metrics_json.exists():
            stored = read_json(target.metrics_json)
            recomputed = {
                "samples": len(answers),
                "retrieval_hit_rate": mean(1.0 if a["retrieval_hit"] else 0.0 for a in answers),
                "mean_token_f1": mean(a["token_f1"] for a in answers),
                "judge_accuracy": mean(1.0 if a["judge"]["correct"] else 0.0 for a in answers),
                "mean_judge_score": mean(a["judge"]["score"] for a in answers),
            }
            mismatches = [
                f"{key}: file={stored.get(key)} recomputed={value:.4f}"
                for key, value in recomputed.items()
                if not isinstance(stored.get(key), (int, float))
                or abs(stored[key] - value) > 1e-6
            ]
            if mismatches:
                print("  FAIL  metrics file does not match its answers file:")
                for mismatch in mismatches:
                    print(f"          {mismatch}")
                failures += 1
            else:
                print("  OK    metrics file is consistent with its answers file")

        # 3. per-question-type breakdown
        by_type: dict[str, list[dict[str, Any]]] = {}
        for item in answers:
            by_type.setdefault(item["question_type"], []).append(item)
        for question_type, items in sorted(by_type.items()):
            hit = mean(1.0 if i["retrieval_hit"] else 0.0 for i in items)
            f1 = mean(i["token_f1"] for i in items)
            print(f"    {question_type:<12} n={len(items):<3} hit_rate={hit:.2f}  token_f1={f1:.4f}")

    compare(settings)

    print(section("Audit result"))
    if failures:
        print(f"  {failures} integrity problem(s) found -- see FAIL lines above")
    else:
        print("  no integrity problems found")
    return 1 if failures else 0


def compare(settings) -> None:
    print(f"\n{'=' * 72}\nCOMPARISON\n{'=' * 72}")
    loaded: dict[str, dict[str, Any]] = {}
    for state in STATES:
        path = state_paths(settings, state).metrics_json
        if path.exists():
            loaded[state] = read_json(path)

    if not loaded:
        print("  no metrics files found yet")
        return

    header = f"  {'metric':<22}" + "".join(f"{state:>14}" for state in loaded)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key in HEADLINE_METRICS:
        row = f"  {key:<22}"
        for state in loaded:
            value = loaded[state].get(key)
            row += f"{value:>14.4f}" if isinstance(value, (int, float)) else f"{'n/a':>14}"
        print(row)

    if "baseline" in loaded:
        print()
        for state in loaded:
            if state == "baseline":
                continue
            print(f"  delta vs baseline -- {state}:")
            for key in HEADLINE_METRICS:
                base, other = loaded["baseline"].get(key), loaded[state].get(key)
                if isinstance(base, (int, float)) and isinstance(other, (int, float)):
                    delta = other - base
                    print(f"    {key:<22} {delta:+.4f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=STATES, default="baseline")
    parser.add_argument("--all", action="store_true", help="evaluate every state that has an index")
    parser.add_argument("--compare", action="store_true", help="only print a comparison of existing metrics")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="check existing artifacts for judge integrity and metric/answer consistency (no LLM calls)",
    )
    args = parser.parse_args()

    settings = load_settings()

    if args.audit:
        return audit(settings)

    if args.compare:
        compare(settings)
        return 0

    print(section("Evaluation Set contract"))
    problems = validate_test_set(settings.paths.eval_testset)
    if problems:
        for problem in problems:
            print(f"  FAIL  {problem}")
        return 1
    test_set = read_json(settings.paths.eval_testset)
    print(f"  OK  {len(test_set)} samples with all 5 required fields")

    targets = STATES if args.all else (args.state,)
    results = {state: run_state(settings, state) for state in targets}

    if sum(1 for value in results.values() if value) > 1 or args.all:
        compare(settings)

    return 0 if any(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
