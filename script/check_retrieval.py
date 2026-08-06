"""Build and smoke-test the ChromaDB vector store collections.

Covers Duty 1 (khoi tao va quan ly 3 ChromaDB collections) and the retrieval
half of Duty 2 (semantic search + lookup work correctly).

Usage
-----
    uv run python script/check_retrieval.py                     # baseline, build if missing
    uv run python script/check_retrieval.py --rebuild           # force re-embed
    uv run python script/check_retrieval.py --state corrupted
    uv run python script/check_retrieval.py --all               # every available state
    uv run python script/check_retrieval.py --all --reset-store # wipe data/chroma/ and rebuild
                                                                # (after a git merge broke the store)

Exit code is 0 when every check passes, 1 otherwise, so this can gate a run.
"""

from __future__ import annotations

import argparse
import shutil
import sys

from _tv3_common import (
    STATES,
    coerce_metadata,
    duplicate_report,
    embedding_truncation_report,
    format_row,
    load_clean_frame,
    section,
    state_paths,
    validate_contract,
)

from core.config import load_settings
from retrieval.index import LocalEmbeddingIndex

SEARCH_SAMPLE_SIZE = 5


def check_state(settings, state: str, rebuild: bool, top_k: int) -> bool:
    target = state_paths(settings, state)
    print(f"\n{'=' * 72}\nSTATE: {state}  ->  collection '{target.collection_name}'\n{'=' * 72}")

    # --- 1. data contract -------------------------------------------------
    try:
        df, source = load_clean_frame(target)
    except FileNotFoundError as exc:
        print(f"  SKIP  {exc}")
        return "SKIP"  # not an error: this state may not exist yet

    print(section("1. Clean Dataset Schema contract"))
    print(format_row("source artifact", source))
    fatal, repairable = validate_contract(df)

    if fatal:
        for problem in fatal:
            print(f"  FAIL  {problem}")
        print("  Dataset is unusable; nothing downstream can run.")
        return False

    # A corrupted dataset is allowed to contain bad values. It is NOT allowed to
    # break the schema contract -- so we report, work around it, and keep going.
    contract_ok = not repairable
    if contract_ok:
        print("  OK  all 10 required columns present and populated")
    else:
        for problem in repairable:
            print(f"  VIOLATION  {problem}")
        print("  Proceeding with a coercion so the state can still be indexed.")

    dupes = duplicate_report(df)
    print(format_row("rows", dupes["rows"]))
    print(format_row("unique paper_id", dupes["unique_paper_ids"]))
    print(format_row("duplicate paper_id rows", dupes["duplicate_rows"]))

    trunc = embedding_truncation_report(df)
    print(section("2. MiniLM truncation exposure (256-token window)"))
    print(format_row("mean words in text_for_embedding", trunc["mean_words"]))
    print(format_row("max words", trunc["max_words"]))
    print(
        format_row(
            "docs over ~200-word budget",
            f"{trunc['docs_over_budget']} of {trunc['docs_total']}",
        )
    )
    if trunc["docs_over_budget"]:
        print(
            "  NOTE  Text past the window is silently discarded. Corruption applied to the\n"
            "        tail of a summary may never reach the vectors."
        )

    # --- 2. build or load the collection ----------------------------------
    print(section("3. ChromaDB collection"))
    indexable, coercions = coerce_metadata(df)
    for note in coercions:
        print(f"  COERCED  {note}  <-- raise this with the artifact's owner")

    if rebuild or not target.embeddings_json.exists():
        action = "rebuilt" if rebuild else "built"
        index = LocalEmbeddingIndex.build(
            df=indexable,
            settings=settings,
            embeddings_output_path=target.embeddings_json,
        )
    else:
        action = "loaded from manifest"
        try:
            index = LocalEmbeddingIndex.load(settings, target.embeddings_json)
        except Exception as exc:
            print(f"  FAIL  could not load existing index ({exc})")
            print(
                "        The manifest names this collection but the Chroma store does not\n"
                "        contain it. This happens after a git merge, because data/chroma/ is\n"
                "        binary and cannot be merged. Fix with:\n"
                "          uv run python script/check_retrieval.py --all --rebuild --reset-store"
            )
            return "FAIL"

    print(format_row("action", action))
    print(format_row("manifest", target.embeddings_json.name))
    print(format_row("persist path", settings.paths.chroma_dir))

    # The collection name is derived from the manifest path, so passing the
    # wrong path silently writes every state into papers-baseline.
    if index.collection_name != target.collection_name:
        print(
            f"  FAIL  collection name is '{index.collection_name}', expected "
            f"'{target.collection_name}'"
        )
        return "FAIL"
    print(f"  OK  collection name is '{index.collection_name}'")

    indexed = index.collection.count()
    print(format_row("vectors in collection", indexed))
    if indexed != len(df):
        print(f"  FAIL  expected {len(df)} vectors, found {indexed}")
        return "FAIL"
    print("  OK  vector count matches row count")

    dimension = len(index.embedding_model.embed_query("dimension probe"))
    print(format_row("embedding dimension", dimension))

    # --- 3. semantic search -----------------------------------------------
    print(section("4. Semantic search"))
    sample = df.head(SEARCH_SAMPLE_SIZE)
    hits = 0
    for _, row in sample.iterrows():
        results = index.search(row["title"], top_k=top_k)
        found = [item for item in results if item.paper_id == row["paper_id"]]
        rank = results.index(found[0]) + 1 if found else None
        hits += 1 if found else 0
        top_score = f"{results[0].score:.4f}" if results else "n/a"
        status = f"rank {rank}" if rank else "MISS"
        print(f"  [{status:>7}]  top_score={top_score}  {str(row['title'])[:56]}")

    print(format_row(f"self-retrieval hit rate (top-{top_k})", f"{hits}/{len(sample)}"))
    if hits != len(sample):
        print("  WARN  a paper did not retrieve itself from its own title -- inspect before trusting metrics")

    print("\n  Cross-topic probes:")
    for query in (
        "retrieval augmented generation for medical diagnosis",
        "agentic large language model tool selection",
        "safety report generation",
    ):
        results = index.search(query, top_k=2)
        if not results:
            print(f"    '{query}' -> no results")
            continue
        best = results[0]
        print(f"    '{query[:44]}' -> {best.score:.4f}  {best.title[:44]}")

    # --- 4. exact lookup --------------------------------------------------
    print(section("5. Exact lookup (paper_id and title)"))
    lookup_ok = True
    for _, row in sample.iterrows():
        by_id = index.lookup(row["paper_id"])
        by_title = index.lookup(row["title"])
        id_ok = by_id is not None and by_id["paper_id"] == row["paper_id"]
        title_ok = by_title is not None and by_title["paper_id"] == row["paper_id"]
        if not (id_ok and title_ok):
            lookup_ok = False
            print(f"  FAIL  id={id_ok} title={title_ok}  {row['paper_id']}")
    if lookup_ok:
        print(f"  OK  {len(sample)} papers resolve by both paper_id and exact title")

    if index.lookup("this-paper-does-not-exist") is not None:
        print("  FAIL  lookup returned a record for a nonsense key")
        lookup_ok = False
    else:
        print("  OK  unknown key returns None")

    if not lookup_ok:
        return "FAIL"
    return "PASS" if contract_ok else "WARN"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=STATES, default="baseline")
    parser.add_argument("--all", action="store_true", help="check every state that has data")
    parser.add_argument("--rebuild", action="store_true", help="force re-embedding")
    parser.add_argument(
        "--reset-store",
        action="store_true",
        help="delete data/chroma/ before building (use after a git merge left the store inconsistent)",
    )
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    settings = load_settings()
    top_k = args.top_k or settings.top_k
    targets = STATES if args.all else (args.state,)

    if args.reset_store:
        chroma_dir = settings.paths.chroma_dir
        if chroma_dir.exists():
            keep = chroma_dir / ".gitkeep"
            for entry in chroma_dir.iterdir():
                if entry == keep:
                    continue
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
            print(f"  reset store: cleared {chroma_dir}")
        if not args.rebuild:
            print("  NOTE  --reset-store implies --rebuild")
        args.rebuild = True

    results = {state: check_state(settings, state, args.rebuild, top_k) for state in targets}

    print(f"\n{'=' * 72}\nSUMMARY\n{'=' * 72}")
    for state, status in results.items():
        note = "  (schema contract violated but worked around)" if status == "WARN" else ""
        print(f"  {state:<12} {status}{note}")

    if args.all:
        built = [
            state_paths(settings, state).collection_name
            for state in STATES
            if state_paths(settings, state).embeddings_json.exists()
        ]
        print(f"\n  collections present: {', '.join(built) if built else 'none'}")
        if len(set(built)) != len(built):
            print("  FAIL  duplicate collection names -- states are overwriting each other")
            return 1

    return 1 if any(status == "FAIL" for status in results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
