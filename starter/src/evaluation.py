from collections import defaultdict
from typing import Any
import re
import unicodedata


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"\s*([=:/%])\s*", r"\1", text)
    text = re.sub(r"\s+", " ", text)

    return text.casefold().strip()


def _is_evidence_hit(
    question: dict[str, Any],
    hit: dict[str, Any],
) -> bool:
    gold_source = str(question["gold_source_id"])
    gold_page = question["gold_page"]
    evidence = _normalize(question["evidence_quote"])

    source_match = (
        str(hit.get("document_id")) == gold_source
        or str(hit.get("source")) == gold_source
    )

    page_match = hit.get("page") == gold_page
    text_match = evidence in _normalize(hit.get("text", ""))

    return source_match and page_match and text_match


def evaluate_query(
    question: dict[str, Any],
    hits: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_hits = [_is_evidence_hit(question, hit) for hit in hits]

    return {
        "question_id": question["id"],
        "split": question["split"],
        "hit_at_1": bool(evidence_hits and evidence_hits[0]),
        "evidence_hit_at_3": any(evidence_hits),
        "matched_positions": [
            index + 1
            for index, matched in enumerate(evidence_hits)
            if matched
        ],
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for trace in traces:
        grouped[(trace["strategy"], trace["split"])].append(trace)

    summary: dict[str, Any] = {}

    for (strategy, split), items in sorted(grouped.items()):
        total = len(items)
        hit_at_1 = sum(item["hit_at_1"] for item in items)
        hit_at_3 = sum(item["evidence_hit_at_3"] for item in items)

        summary[f"{strategy}:{split}"] = {
            "hit_at_1_count": hit_at_1,
            "hit_at_1_total": total,
            "hit_at_1": hit_at_1 / total if total else 0,
            "evidence_hit_at_3_count": hit_at_3,
            "evidence_hit_at_3_total": total,
            "evidence_hit_at_3": hit_at_3 / total if total else 0,
        }

    return summary
