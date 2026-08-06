"""Demonstrate the RAG agent and test that it refuses to answer outside the corpus.

Covers the agent half of Duty 2. Two question groups are run:

  in-corpus      answerable from the 24 indexed papers; the agent should call a
                 tool and answer from retrieved content
  out-of-corpus  plausible-sounding papers that were never indexed; the agent
                 should say it cannot find them

The system prompt in `src/retrieval/agent.py` instructs exactly this ("If the
indexed corpus does not support the answer, say so clearly"), so the second
group is the evidence that the instruction actually holds.

Writes `data/results/agent_demo_answers.json`.

Usage
-----
    uv run python script/run_agent_demo.py
    uv run python script/run_agent_demo.py --state corrupted
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from _tv3_common import STATES, format_row, load_clean_frame, section, state_paths

from core.config import load_settings
from core.utils import write_json
from retrieval.agent import build_agent
from retrieval.index import LocalEmbeddingIndex

# Papers that do not exist. If the agent answers these with confident detail
# rather than admitting ignorance, it is hallucinating.
OUT_OF_CORPUS_QUESTIONS = [
    "What does the paper 'Quantum Tunneling Effects in Avian Magnetoreception' conclude?",
    "Who authored the paper 'Self-Replicating Transformer Architectures for Lunar Robotics'?",
    "Summarise the main finding of the 2019 study on retrieval-augmented generation in veterinary dentistry.",
]

# Phrases that indicate a proper refusal rather than a fabricated answer.
#
# NOTE: the first version of this list missed "couldn't find", which is the
# phrasing gpt-4o-mini actually uses, so a run where the agent refused all three
# out-of-corpus questions correctly was reported as 0/3. Contractions are the
# obvious gap in any keyword heuristic -- keep both forms of every verb.
REFUSAL_MARKERS = (
    "not find",
    "couldn't find",
    "could not find",
    "didn't find",
    "did not find",
    "no exact",
    "does not",
    "doesn't",
    "not in",
    "not available",
    "not present",
    "cannot",
    "can't",
    "unable",
    "no paper",
    "no information",
    "not support",
    "don't have",
    "do not have",
    "no match",
    "no specific",
    "isn't",
    "is not",
)


def extract_trace(result: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    """Pull the final answer and the tool calls out of an agent invocation."""
    messages = result.get("messages", [])
    tool_calls: list[dict[str, Any]] = []
    for message in messages:
        for call in getattr(message, "tool_calls", None) or []:
            if isinstance(call, dict):
                tool_calls.append({"name": call.get("name"), "args": call.get("args")})
            else:
                tool_calls.append({"name": getattr(call, "name", None), "args": getattr(call, "args", None)})
    if not messages:
        return "", tool_calls
    final = messages[-1]
    return str(getattr(final, "content", final)), tool_calls


def looks_like_refusal(answer: str) -> bool:
    lowered = answer.lower()
    return any(marker in lowered for marker in REFUSAL_MARKERS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", choices=STATES, default="baseline")
    args = parser.parse_args()

    settings = load_settings()
    target = state_paths(settings, args.state)

    if not target.embeddings_json.exists():
        print(f"  FAIL  no index for state '{args.state}'. Run check_retrieval.py first.")
        return 1

    df, _ = load_clean_frame(target)
    index = LocalEmbeddingIndex.load(settings, target.embeddings_json)

    print(section("Setup"))
    print(format_row("state", args.state))
    print(format_row("collection", index.collection_name))
    print(format_row("provider / model", f"{settings.llm_provider} / {settings.model_name}"))

    try:
        agent = build_agent(settings=settings, index=index)
    except Exception as exc:
        print(f"  FAIL  could not build agent: {type(exc).__name__}: {exc}")
        print("  Run script/check_llm.py to diagnose the provider.")
        return 1

    # Build in-corpus questions from real rows so ground truth is checkable.
    sample = df.head(3)
    in_corpus = []
    for _, row in sample.iterrows():
        in_corpus.append(
            {
                "question": f"Who authored the paper '{row['title']}'?",
                "expected_paper_id": row["paper_id"],
                "expected_contains": str(row["authors_joined"]).split(",")[0].strip(),
            }
        )
    in_corpus.append(
        {
            "question": "Which indexed papers discuss retrieval-augmented generation in a clinical or medical setting?",
            "expected_paper_id": None,
            "expected_contains": None,
        }
    )

    records: list[dict[str, Any]] = []

    print(section("A. In-corpus questions (agent should answer from retrieved content)"))
    for item in in_corpus:
        try:
            answer, tool_calls = extract_trace(
                agent.invoke({"messages": [{"role": "user", "content": item["question"]}]})
            )
        except Exception as exc:
            print(f"  ERROR  {type(exc).__name__}: {exc}")
            return 1

        used_tools = [call["name"] for call in tool_calls]
        grounded = bool(used_tools)
        contains = (
            item["expected_contains"].lower() in answer.lower()
            if item["expected_contains"]
            else None
        )
        verdict = "OK" if grounded and contains is not False else "REVIEW"

        print(f"\n  [{verdict}] {item['question'][:88]}")
        print(f"        tools: {used_tools or 'NONE  <-- answered without retrieving'}")
        print(f"        answer: {answer[:150]}")
        if contains is False:
            print(f"        expected to mention: {item['expected_contains']}")

        records.append(
            {
                "group": "in_corpus",
                "question": item["question"],
                "answer": answer,
                "tool_calls": tool_calls,
                "used_tools": grounded,
                "expected_paper_id": item["expected_paper_id"],
                "expected_contains": item["expected_contains"],
                "contains_expected": contains,
            }
        )

    print(section("B. Out-of-corpus questions (agent should refuse)"))
    refusals = 0
    for question in OUT_OF_CORPUS_QUESTIONS:
        try:
            answer, tool_calls = extract_trace(
                agent.invoke({"messages": [{"role": "user", "content": question}]})
            )
        except Exception as exc:
            print(f"  ERROR  {type(exc).__name__}: {exc}")
            return 1

        refused = looks_like_refusal(answer)
        refusals += 1 if refused else 0
        print(f"\n  [{'REFUSED' if refused else 'HALLUCINATED?'}] {question[:80]}")
        print(f"        tools: {[call['name'] for call in tool_calls] or 'NONE'}")
        print(f"        answer: {answer[:200]}")

        records.append(
            {
                "group": "out_of_corpus",
                "question": question,
                "answer": answer,
                "tool_calls": tool_calls,
                "used_tools": bool(tool_calls),
                "refused": refused,
            }
        )

    print(section("Result"))
    print(format_row("in-corpus questions", len(in_corpus)))
    print(
        format_row(
            "grounded in a tool call",
            f"{sum(1 for r in records if r['group'] == 'in_corpus' and r['used_tools'])}/{len(in_corpus)}",
        )
    )
    print(format_row("out-of-corpus refusals", f"{refusals}/{len(OUT_OF_CORPUS_QUESTIONS)}"))
    if refusals < len(OUT_OF_CORPUS_QUESTIONS):
        print(
            "  WARN  at least one out-of-corpus answer did not read as a refusal.\n"
            "        The keyword check is a heuristic -- read the answers before reporting."
        )

    write_json(settings.paths.demo_answers, records)
    print(f"\n  wrote {settings.paths.demo_answers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
