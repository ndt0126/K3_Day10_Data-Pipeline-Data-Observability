from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, normalize_whitespace, write_json


_REQUIRED_COLUMNS = {
    "paper_id",
    "title",
    "summary",
    "authors_joined",
    "categories_joined",
    "published",
}
_MINIMUM_DOCUMENTS = 4
_QUESTION_TYPES = ("summary", "authors", "date", "categories")


def _text(value: object) -> str:
    return normalize_whitespace(value) if isinstance(value, str) else ""


def _question_samples(row: dict[str, Any], document_number: int) -> list[dict[str, Any]]:
    """Build factual, exact-title questions whose answers come from one document."""
    paper_id = _text(row["paper_id"])
    title = _text(row["title"])
    summary = _text(row["summary"])
    authors = _text(row["authors_joined"])
    categories = _text(row["categories_joined"])
    published = _text(row["published"])

    prompts_and_answers = [
        ("summary", f"What does the paper '{title}' describe?", first_sentence(summary)),
        ("authors", f"Who authored the paper '{title}'?", authors),
        ("date", f"When was the paper '{title}' published?", published),
        ("categories", f"What categories does the paper '{title}' belong to?", categories),
    ]
    return [
        {
            "id": f"eval-{document_number:02d}-{question_type}",
            "question_type": question_type,
            "question": question,
            "ground_truth": answer,
            "ground_truth_doc_ids": [paper_id],
        }
        for question_type, question, answer in prompts_and_answers
    ]


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Create and persist a deterministic evaluation set from clean data.

    The selection is sorted by stable paper ID, so rerunning on the same clean
    snapshot produces the same questions.  Each question points to a real
    ``paper_id`` that exists in the embedding index input.
    """
    missing_columns = sorted(_REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError(f"Clean dataframe is missing required columns: {', '.join(missing_columns)}")

    candidates = df.loc[:, sorted(_REQUIRED_COLUMNS)].copy()
    for column in _REQUIRED_COLUMNS:
        candidates[column] = candidates[column].map(_text)
    candidates = candidates.loc[
        (candidates["paper_id"] != "")
        & (candidates["title"] != "")
        & (candidates["summary"] != "")
        & (candidates["authors_joined"] != "")
        & (candidates["categories_joined"] != "")
        & (candidates["published"] != "")
    ]
    candidates = candidates.drop_duplicates(subset="paper_id").sort_values("paper_id", kind="stable")

    if len(candidates) < _MINIMUM_DOCUMENTS:
        raise ValueError(
            "At least "
            f"{_MINIMUM_DOCUMENTS} complete clean documents are required to build the evaluation set; "
            f"found {len(candidates)}."
        )

    # Four documents × four question types gives a concise but representative,
    # fixed evaluation set that can be reused for corrupted and repaired runs.
    selected = candidates.head(_MINIMUM_DOCUMENTS).to_dict(orient="records")
    test_set = [
        sample
        for document_number, row in enumerate(selected, start=1)
        for sample in _question_samples(row, document_number)
    ]
    assert {sample["question_type"] for sample in test_set} == set(_QUESTION_TYPES)

    write_json(Path(output_path), test_set)
    return test_set
