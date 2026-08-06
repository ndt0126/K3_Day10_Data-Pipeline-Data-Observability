"""Verify the configured LLM provider before spending time on a full run.

Covers the multi-provider half of Duty 2. Run this first: a bad key surfaces
here in two seconds instead of twenty minutes into an evaluation -- and more
importantly, `metrics.py::_judge_answer` swallows every exception and silently
falls back to a token-F1 heuristic, so a broken key still produces
`judge_accuracy` numbers that look plausible and mean nothing.

Usage
-----
    uv run python script/check_llm.py
"""

from __future__ import annotations

import sys

from _tv3_common import format_row, section

from core.config import load_settings, normalized_provider, require_llm_credentials
from evaluation.metrics import JudgeVerdict
from retrieval.llm import build_llm

PROVIDER_KEY_FIELD = {
    "openai": "openai_api_key",
    "gemini": "google_api_key",
    "anthropic": "anthropic_api_key",
    "openrouter": "openrouter_api_key",
    "custom": "custom_llm_api_key",
    "ollama": None,
}


def main() -> int:
    settings = load_settings()
    provider = normalized_provider(settings)

    print(section("1. Configuration"))
    print(format_row("LLM_PROVIDER", settings.llm_provider))
    print(format_row("normalized provider", provider))
    print(format_row("LLM_MODEL", settings.model_name))

    key_field = PROVIDER_KEY_FIELD.get(provider)
    if key_field:
        key = getattr(settings, key_field, None)
        if key:
            print(format_row("credential", f"present ({key[:6]}...{key[-4:]}, len {len(key)})"))
        else:
            print(format_row("credential", "MISSING"))

    print(section("2. Credential validation"))
    try:
        require_llm_credentials(settings)
        print("  OK  credentials satisfy the provider requirement")
    except RuntimeError as exc:
        print(f"  FAIL  {exc}")
        print("\n  Fix .env, then re-run. Nothing else in this script can pass.")
        return 1

    print(section("3. Client construction"))
    try:
        llm = build_llm(settings=settings, temperature=0.0)
        print(f"  OK  built {type(llm).__name__}")
    except Exception as exc:
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        return 1

    print(section("4. Live completion"))
    try:
        response = llm.invoke("Reply with exactly the word: ready")
        text = getattr(response, "content", str(response))
        print(format_row("response", repr(text)[:80]))
        print("  OK  the provider answered")
    except Exception as exc:
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        print("\n  Common causes: wrong key, no billing/quota, model name not available to this account.")
        return 1

    # The judge calls .with_structured_output(JudgeVerdict). Some providers and
    # some smaller models do not support tool/function calling, and the failure
    # is invisible because _judge_answer catches everything.
    print(section("5. Structured output (required by the LLM judge)"))
    try:
        judge = llm.with_structured_output(JudgeVerdict)
        verdict = judge.invoke(
            "Evaluate the model answer against the reference answer.\n"
            "Question: What is the capital of France?\n"
            "Reference answer: Paris\n"
            "Model answer: Paris\n"
            "Return: score from 1 to 5, correct = true only when materially correct, short reasoning."
        )
        print(format_row("score", verdict.score))
        print(format_row("correct", verdict.correct))
        print(format_row("reasoning", verdict.reasoning[:60]))
        if not verdict.correct:
            print("  WARN  judge marked an obviously correct answer wrong -- model may be too weak")
        print("  OK  structured output works; the judge will use the LLM, not the fallback heuristic")
    except Exception as exc:
        print(f"  FAIL  {type(exc).__name__}: {exc}")
        print(
            "\n  The judge will silently fall back to a token-F1 heuristic and\n"
            "  judge_accuracy / mean_judge_score will not reflect an LLM at all.\n"
            "  Pick a model that supports tool calling before running the evaluation."
        )
        return 1

    print(section("Result"))
    print(f"  PASS  provider '{provider}' with model '{settings.model_name}' is ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
