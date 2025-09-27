#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Score Hungarian 3-chunk word combinations and optionally add a simple joke.

Rules (concise):
- Score 1: not a plausible separate-words phrase; leave joke empty.
- Score 2: borderline/plausible but weak; leave joke empty.
- Score 3+: plausible and potentially funny; add joke as the chunk phrase
  (e.g., "is te nem").

Heuristics:
- Prefer when all three chunks are valid Hungarian words (via wordfreq or
  function-word whitelist).
- Reward combos with function words and/or iconic noun-y triples
  (e.g., kan + dal + ló; vas + ár + nap; te + le + fon).
- Preserve existing non-empty score/joke fields.

Usage:
  python -m word_jokes.score_3_element_combos \
    --input word_jokes/3_element_word_comibations_scored.csv \
    --output word_jokes/3_element_word_comibations_scored.csv \
    [--backup word_jokes/3_element_word_comibations_scored.bak.csv]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Set, Tuple


def load_wordfreq():
    # We intentionally avoid relying heavily on wordfreq to stay strict.
    # Keep import optional for potential future tweaks, but do not use by default.
    try:
        from wordfreq import zipf_frequency  # type: ignore
        return zipf_frequency
    except Exception:
        return None


def build_sets() -> tuple[Set[str], Set[str], Set[Tuple[str, str, str]], Set[str]]:
    # Common Hungarian function words and short words that are valid alone.
    function_words = {
        # articles / determiners
        "a", "az", "egy",
        # conjunctions / particles / adverbs
        "és", "de", "vagy", "mert", "ha", "mint", "hogy", "is", "sem", "se",
        "csak", "már", "még", "igen", "nem", "na", "ja", "hát", "itt", "ott",
        "így", "úgy", "le", "fel", "be", "ki", "el", "át", "rá", "alá", "túl",
        # pronouns
        "én", "te", "ő", "mi", "ti", "ők", "engem", "téged", "őt", "minket",
        "titeket", "őket",
        # very common short lemmas
        "van", "volt", "jó", "rossz", "hol",
    }

    # Tokens that look like suffix/fragments — discourage counting as words.
    suffix_like = {
        "tt", "mm", "bb", "nn", "ss", "kk",
        "ni", "an", "en", "on", "al", "el", "ul", "ül", "am", "em", "om",
        "at", "et", "ot", "át", "ék", "ik", "na", "ne", "ná", "né",
    }

    # A very small content-word whitelist that often makes iconic triples.
    content_words = {
        "kan", "dal", "ló", "vas", "ár", "nap", "fon",
    }

    # Iconic/funny triples to boost.
    special_triples = {
        ("is", "te", "nem"),
        ("te", "le", "fon"),
        ("vas", "ár", "nap"),
        ("kan", "dal", "ló"),
    }

    return function_words, suffix_like, special_triples, content_words


def is_valid_word(token: str) -> bool:
    function_words, suffix_like, _, content_words = build_sets()
    t = token.strip().lower()
    if not t:
        return False
    if t in function_words:
        return True
    if t in suffix_like:
        return False
    # One-letter words are rarely valid besides "a"; already covered above via function_words.
    if len(t) == 1:
        return False
    # Two-letter tokens: accept only if explicitly known-functional or whitelisted content.
    if len(t) == 2:
        return t in function_words or t in {"ló", "ár"}
    # Longer tokens: accept only if in our small content whitelist.
    return t in content_words


def score_row(c1: str, c2: str, c3: str, corpus: str, zipf_frequency) -> int:
    function_words, suffix_like, special_triples, content_words = build_sets()
    t1, t2, t3 = c1.strip().lower(), c2.strip().lower(), c3.strip().lower()

    # Basic validity checks
    v1 = is_valid_word(t1)
    v2 = is_valid_word(t2)
    v3 = is_valid_word(t3)
    valid_count = (1 if v1 else 0) + (1 if v2 else 0) + (1 if v3 else 0)

    # Default strictly low unless strong signals
    if valid_count < 2:
        return 1

    # Two valid words: borderline
    if valid_count == 2:
        # Slight bump if the two valid are function words forming plausible misunderstanding
        fun_count = (t1 in function_words) + (t2 in function_words) + (t3 in function_words)
        if fun_count >= 2:
            return 2
        return 2

    # All three valid: base good
    score = 3

    # Special iconic triples get boosted
    if (t1, t2, t3) in special_triples:
        score = max(score, 4)

    # Reward mixes with function words that can sound like a quip
    fun_count = (t1 in function_words) + (t2 in function_words) + (t3 in function_words)
    if fun_count >= 2:
        score = max(score, 3)

    # Reward nouny triples like kan+dal+ló, vas+ár+nap by detecting common roots
    content_hits = sum(t in content_words for t in (t1, t2, t3))
    if content_hits >= 2:
        score = max(score, 4)

    # Clamp range 1..5
    return max(1, min(score, 5))


def make_joke(c1: str, c2: str, c3: str, corpus: str, score: int) -> str:
    # Keep it minimal per the examples — just the phrase for >=3.
    if score >= 3:
        return f"{c1} {c2} {c3}"
    return ""


def process_csv(inp: Path, outp: Path, backup: Path | None) -> tuple[int, int, int]:
    zipf_frequency = load_wordfreq()

    with inp.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    updated = 0
    preserved = 0
    total = len(rows)

    for row in rows:
        # Skip if already scored
        if (row.get("score") or "").strip():
            preserved += 1
            continue
        c1 = row.get("chunk1", "")
        c2 = row.get("chunk2", "")
        c3 = row.get("chunk3", "")
        corpus = row.get("corpus", "")
        sc = score_row(c1, c2, c3, corpus, zipf_frequency)
        joke = make_joke(c1, c2, c3, corpus, sc)
        # Fill per user guidance: write score for all; only give joke if score > 2.
        row["score"] = str(sc) if sc else ""
        row["joke"] = joke if sc and sc > 2 else ""
        updated += 1

    # Backup if requested
    if backup is not None:
        backup.write_text(inp.read_text(encoding="utf-8"), encoding="utf-8")

    # Write output, preserving header order
    fieldnames = ["corpus", "chunk1", "chunk2", "chunk3", "score", "joke"]
    with outp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})

    return total, preserved, updated


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=False, default="word_jokes/3_element_word_comibations_scored.csv")
    ap.add_argument("--output", required=False, default="word_jokes/3_element_word_comibations_scored.csv")
    ap.add_argument("--backup", required=False, default="word_jokes/3_element_word_comibations_scored.bak.csv")
    ap.add_argument("--recalculate-all", action="store_true", help="Ignore existing scores and recompute for all rows")
    args = ap.parse_args()

    inp = Path(args.input)
    outp = Path(args.output)
    backup = Path(args.backup) if args.backup else None

    if args.recalculate_all:
        # Load, wipe scores, then process to force recalculation
        with inp.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        for row in rows:
            row["score"] = ""
            row["joke"] = ""
        # Write wiped temp
        fieldnames = ["corpus", "chunk1", "chunk2", "chunk3", "score", "joke"]
        tmp = inp.with_suffix(".tmp.csv")
        with tmp.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for row in rows:
                w.writerow({k: row.get(k, "") for k in fieldnames})
        # Replace input for processing
        inp = tmp

    total, preserved, updated = process_csv(inp, outp, backup)
    print(f"Processed: {total} rows; preserved: {preserved}; updated: {updated}")


if __name__ == "__main__":
    main()
