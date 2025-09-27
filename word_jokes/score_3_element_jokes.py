#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scores 3-element Hungarian word-split jokes and updates the CSV in-place.

Heuristics (strict by design):
- Default score is 1 (leave blank in output for 1).
- Count recognized tokens among chunk1, chunk2, chunk3.
  - Recognized if:
    * in curated Hungarian function-word set, or
    * in case/post-position set, or
    * is a 1-letter suffix token from a curated set, or
    * has sufficient word frequency in Hungarian (via wordfreq).
- Score mapping:
  - <2 recognized -> 1
  - 2 recognized  -> 2
  - 3 recognized  -> 3, possibly 4 with favorable pattern
  - Special boosts from findings/examples can push to 4–5
- For score >= 3, propose a simple "joke" phrase using the 3 chunks
  with light hyphenation rules (e.g., "a-t").

Note: We keep it strict and conservative. Many rows remain 1.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import List, Set, Dict

try:
    from wordfreq import zipf_frequency
except Exception:  # pragma: no cover
    def zipf_frequency(word: str, lang: str = "hu") -> float:
        # Fallback if wordfreq is missing; acts as unknown
        return 0.0


VOCALS = set("aáeéiíoóöőuúüű")

# Common Hungarian function words and short words that help form plausible phrases
HU_FUNCTION_WORDS: Set[str] = {
    # articles, conjunctions, particles
    "a", "az", "és", "vagy", "de", "mert", "hogy", "ha", "is", "se", "semmis", "meg",
    "már", "még", "sem", "mint", "s", "no", "na", "csak", "pedig", "ám", "bár",
    # pronouns
    "én", "te", "ő", "mi", "ti", "ők", "engem", "téged", "őt", "minket", "titeket", "őket",
    # question words
    "ki", "mi", "mit", "mikor", "hol", "hova", "miért", "hogyan", "hogyan",
    # adverbs/common
    "itt", "ott", "ide", "oda", "fent", "lent", "kint", "bent", "fel", "le", "át", "vissza",
    # auxiliaries/common verbs (inflected short forms)
    "van", "volt", "lesz", "légy", "légyen",
}

# Case markers, postpositions, and common 2–3 letter particles that often appear standalone
HU_CASE_POST: Set[str] = {
    # 1–2 char case/postpos variants (with/without accents)
    "ra", "re", "rá", "ré", "ba", "be", "ban", "ben",
    "on", "en", "ön", "n",
    "hoz", "hez", "höz",
    "val", "vel",
    "tol", "tól", "tol", "től", "rol", "ról", "rol", "ről",
    "nal", "nál", "nel", "nél",
    "ig", "ért", "kent", "ként",
}

# Single-letter suffix-like tokens frequently used in puns (accusative etc.)
SUFFIX_LETTERS: Set[str] = {"t", "d", "m", "n", "k", "s", "r"}


def is_hu_word_by_freq(tok: str) -> bool:
    # Use a fairly strict threshold; keep language noise low
    try:
        z = zipf_frequency(tok, "hu")
    except Exception:
        z = 0.0
    # Consider known functional tokens regardless of freq
    if tok in HU_FUNCTION_WORDS or tok in HU_CASE_POST or tok in SUFFIX_LETTERS:
        return True
    # Very short tokens need to be in curated sets
    if len(tok) <= 2:
        return False
    # Require presence of a Hungarian vowel to look like a content word
    if not any(ch in VOCALS for ch in tok):
        return False
    # Frequency cutoff: be strict to avoid false positives like 'ren'
    return z >= 4.8


def recognized_token(tok: str) -> bool:
    t = tok.strip().lower()
    if not t:
        return False
    if t in HU_FUNCTION_WORDS or t in HU_CASE_POST or t in SUFFIX_LETTERS:
        return True
    return is_hu_word_by_freq(t)


def favorable_pattern(ch1: str, ch2: str, ch3: str) -> bool:
    t1, t2, t3 = ch1.lower(), ch2.lower(), ch3.lower()
    # Patterns like: pronoun + case/postposition + noun/verb-like
    if t1 in {"te", "én", "ő", "mi", "ti", "ők"} and (t2 in HU_CASE_POST or t2 in {"rá", "re", "ba", "be", "át", "le", "fel"}):
        return True
    # Article + noun/verb + accusative 't'
    if t1 in {"a", "az"} and t3 in {"t"}:
        return True
    # Common adverb/preverb + verb-like tail
    if t1 in {"át", "fel", "le", "be", "ki", "vissza", "össze", "szét"} and is_hu_word_by_freq(t2):
        return True
    return False


def boost_from_findings(corpus: str, findings_map: Dict[str, int]) -> int:
    key = corpus.strip().lower()
    return findings_map.get(key, 0)


def build_findings_boosts(findings_path: Path) -> Dict[str, int]:
    boosts: Dict[str, int] = {}
    if not findings_path.exists():
        return boosts
    for raw in findings_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        # Lines with an 'X' mark are strong positives
        if line.endswith("X"):
            word = line[:-1].strip().lower()
            # strip arrows and split hints
            word = word.split("→", 1)[0].strip()
            boosts[word] = max(boosts.get(word, 0), 2)  # strong boost
        # Include explicit examples (no X) with a smaller boost
        elif "→" in line:
            word = line.split("→", 1)[0].strip().lower()
            boosts[word] = max(boosts.get(word, 0), 1)
        else:
            # Raw word lines (no arrow) — light boost
            w = line.split()[0].strip().lower()
            if w:
                boosts[w] = max(boosts.get(w, 0), 1)
    # Also hardcode classic examples from the prompt
    for extra in ["árnyalat", "közösülés", "dehidratál", "terápia", "terápiát"]:
        boosts.setdefault(extra, 2)
    return boosts


def propose_joke(ch1: str, ch2: str, ch3: str) -> str:
    # Basic rendering with minimal hyphenation rules
    toks = [ch1.strip(), ch2.strip(), ch3.strip()]
    out: List[str] = []
    for i, t in enumerate(toks):
        low = t.lower()
        if i > 0 and low in {"t"}:  # attach accusative to previous if previous is an article
            if out and out[-1].lower() in {"a", "az"}:
                out[-1] = f"{out[-1]}-{t}"
            else:
                out.append(t)
        else:
            out.append(t)
    return " ".join(out)


def score_row(corpus: str, ch1: str, ch2: str, ch3: str, findings_boosts: Dict[str, int]) -> (int, str):
    r1 = recognized_token(ch1)
    r2 = recognized_token(ch2)
    r3 = recognized_token(ch3)
    recognized = sum([r1, r2, r3])

    base = 1
    if recognized <= 1:
        base = 1
    elif recognized == 2:
        base = 2
    else:  # all three recognized
        base = 3
        if favorable_pattern(ch1, ch2, ch3):
            base = 4

    base += boost_from_findings(corpus, findings_boosts)
    if base > 5:
        base = 5
    if base < 1:
        base = 1

    joke = ""
    if base >= 3:
        joke = propose_joke(ch1, ch2, ch3)
    return base, joke


def main() -> int:
    path = Path("word_jokes/3_element_word_comibations_scored.csv")
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        return 2

    # Read CSV (expects headers: corpus,chunk1,chunk2,chunk3,score)
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        # Ensure needed columns exist
        needed = ["corpus", "chunk1", "chunk2", "chunk3"]
        for k in needed:
            if k not in fieldnames:
                print(f"Missing column '{k}' in CSV", file=sys.stderr)
                return 3
        if "joke" not in fieldnames:
            fieldnames = fieldnames + ["joke"]
        if "score" not in fieldnames:
            fieldnames = fieldnames + ["score"]
        for row in reader:
            rows.append(row)

    findings_boosts = build_findings_boosts(Path("word_jokes/findings"))

    # Score rows
    for row in rows:
        corpus = (row.get("corpus") or "").strip()
        ch1 = (row.get("chunk1") or "").strip()
        ch2 = (row.get("chunk2") or "").strip()
        ch3 = (row.get("chunk3") or "").strip()
        score, joke = score_row(corpus, ch1, ch2, ch3, findings_boosts)
        # Leave score blank for 1
        row["score"] = ("" if score == 1 else str(score))
        row["joke"] = (joke if score >= 3 else "")

    # Write back
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["corpus", "chunk1", "chunk2", "chunk3", "score", "joke"])
        writer.writeheader()
        for row in rows:
            # Ensure columns exist in right order
            out = {
                "corpus": row.get("corpus", ""),
                "chunk1": row.get("chunk1", ""),
                "chunk2": row.get("chunk2", ""),
                "chunk3": row.get("chunk3", ""),
                "score": row.get("score", ""),
                "joke": row.get("joke", ""),
            }
            writer.writerow(out)

    print(f"Updated: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
