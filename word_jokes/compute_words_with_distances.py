#!/usr/bin/env python3
"""
Enrich word combination CSVs with embedding distances, lengths, and log frequencies.

Features
- Loads a 2..5-element combinations CSV (columns: corpus, chunk1..chunkK).
- Embeds tokens with a multilingual SOTA model (default: intfloat/multilingual-e5-large).
- Computes a single distance metric (default: cosine) for:
  - All pairwise chunk pairs present
  - corpus ↔ each present chunk
- Adds: length_* and logfreq_* for corpus and chunks using hu_50k.txt.

Usage
  python word_jokes/compute_words_with_distances.py --k 3 --metric euclidean --model google/embeddinggemma-300m

Notes
- Metric: cosine is recommended for clustering in embedding space (scale-invariant).
- If you use KMeans with cosine, normalize vectors first (this script does for cosine).
- Log frequency uses natural log: log1p(count). Missing words map to NaN.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
except Exception:
    SentenceTransformer = None  # type: ignore

try:
    import torch  # type: ignore
    from transformers import AutoModel, AutoTokenizer  # type: ignore
except Exception:
    torch = None  # type: ignore


DEFAULT_MODEL = "intfloat/multilingual-e5-large"
ALT_MODELS = [
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "distiluse-base-multilingual-cased-v2",
]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    # Convenience selector: choose k=2..5 instead of paths
    ap.add_argument("--k", type=int, choices=[2, 3, 4, 5],
                    help="If set, uses word_jokes/{k}_element_word_comibations.csv and auto output name")
    # Manual paths (optional when --k is used)
    ap.add_argument("--input", required=False, help="Path to combinations CSV (2..5 elements)")
    ap.add_argument("--output", required=False, help="Path to write enriched CSV")
    ap.add_argument("--metric", choices=["cosine", "euclidean"], default="cosine",
                    help="Distance metric to compute (single metric only)")
    ap.add_argument("--model", default=DEFAULT_MODEL,
                    help=(
                        "Sentence embedding model. Defaults to multilingual e5 large (strong multilingual).\n"
                        f"Alternatives: {', '.join(ALT_MODELS)}"
                    ))
    ap.add_argument("--freq-file", default="word_jokes/hu_50k.txt",
                    help="Word frequency file (space-separated: 'szavak count')")
    ap.add_argument("--batch-size", type=int, default=2048, help="Embedding batch size for unique tokens")
    args = ap.parse_args()

    # Derive input/output from --k if provided
    if args.k is not None:
        # Use the repo's existing naming (note the 'comibations' spelling)
        args.input = args.input or f"word_jokes/{args.k}_element_word_comibations.csv"
        args.output = args.output or f"word_jokes/words_with_distances_{args.k}.csv"

    # Validate presence of paths if --k was not provided
    if args.input is None or args.output is None:
        ap.error("Provide either --k (2..5) or both --input and --output")

    return args


def load_freqs(path: str) -> Dict[str, float]:
    df = pd.read_csv(path, sep=" ", on_bad_lines="skip", dtype=str).dropna()
    # Expect header: szavak count
    if df.columns.size >= 2:
        word_col = df.columns[0]
        count_col = df.columns[1]
    else:
        raise ValueError("Unexpected frequency file format; need two columns")
    # Build lowercase -> log1p(count)
    counts = (
        df[[word_col, count_col]]
        .assign(**{count_col: pd.to_numeric(df[count_col], errors="coerce")})
        .dropna()
    )
    return {str(w).lower(): float(np.log10(c+1)) for w, c in counts.values}


def ensure_columns(df: pd.DataFrame, k: Optional[int]) -> pd.DataFrame:
    # Ensure required structure for the chosen k
    if "corpus" not in df.columns:
        df["corpus"] = np.nan
    max_k = k if k is not None else 5
    for i in range(1, max_k + 1):
        c = f"chunk{i}"
        if c not in df.columns:
            df[c] = np.nan
    # Normalize blanks to NaN
    cols = ["corpus"] + [f"chunk{i}" for i in range(1, max_k + 1)]
    for c in cols:
        df[c] = df[c].astype(str).replace({"": np.nan, "nan": np.nan})
    # Infer or set count_of_chunks
    if "count_of_chunks" not in df.columns:
        if k is not None:
            df["count_of_chunks"] = int(k)
        else:
            up_to = [f"chunk{i}" for i in range(1, max_k + 1)]
            df["count_of_chunks"] = df[up_to].notna().sum(axis=1)
    return df


def build_vocab(df: pd.DataFrame, chunk_cols: List[str]) -> List[str]:
    toks = set()
    toks.update(df["corpus"].dropna().astype(str).tolist())
    for c in chunk_cols:
        if c in df.columns:
            toks.update(df[c].dropna().astype(str).tolist())
    toks = sorted(t for t in toks if isinstance(t, str) and len(t) > 0)
    return toks


def determine_k(args: argparse.Namespace, df: pd.DataFrame) -> int:
    if getattr(args, "k", None) is not None:
        return int(args.k)
    # Try from count_of_chunks if consistent
    if "count_of_chunks" in df.columns:
        vals = sorted(pd.to_numeric(df["count_of_chunks"], errors="coerce").dropna().astype(int).unique())
        if len(vals) == 1 and 2 <= vals[0] <= 5:
            return int(vals[0])
    # Infer from present chunk columns per row and require consistency
    cols = [c for c in df.columns if c.startswith("chunk")]
    if cols:
        counts = df[[c for c in cols if c.startswith("chunk")]].notna().sum(axis=1)
        vals = sorted(counts.unique())
        if len(vals) == 1 and 2 <= vals[0] <= 5:
            return int(vals[0])
    raise SystemExit("Could not determine k. Provide --k (2..5) or a consistent count_of_chunks column.")


def encode_tokens(model: SentenceTransformer, tokens: List[str], batch_size: int, metric: str) -> Dict[str, np.ndarray]:
    mapping: Dict[str, np.ndarray] = {}
    for i in tqdm(range(0, len(tokens), batch_size), desc="Encoding vocab"):
        batch = tokens[i : i + batch_size]
        Z = model.encode(batch, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False)
        if metric == "cosine":
            # Normalize to unit vectors for cosine distance = 1 - dot
            norms = np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12
            Z = Z / norms
        mapping.update(zip(batch, Z))
    return mapping


def d_cosine(u: np.ndarray | None, v: np.ndarray | None) -> float:
    if u is None or v is None:
        return float("nan")
    # With pre-normalized vectors, cosine distance = 1 - dot
    return float(1.0 - float(np.dot(u, v)))


def d_euclid(u: np.ndarray | None, v: np.ndarray | None) -> float:
    if u is None or v is None:
        return float("nan")
    return float(np.linalg.norm(u - v))


def main() -> None:
    args = parse_args()

    print(f"Loading input: {args.input}")
    df = pd.read_csv(args.input)
    k = determine_k(args, df)
    df = ensure_columns(df, k)

    print(f"Loading frequencies: {args.freq_file}")
    freq = load_freqs(args.freq_file)

    print(f"Loading model: {args.model}")

    encoder_fn = None
    backend = None
    # Try sentence-transformers first (fast path)
    if SentenceTransformer is not None:
        try:
            st_model = SentenceTransformer(args.model)
            backend = "sentence-transformers"

            def encoder_fn(texts):
                Z = st_model.encode(
                    list(texts),
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=False,
                )
                if args.metric == "cosine":
                    norms = np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12
                    Z = Z / norms
                return Z

        except Exception:
            encoder_fn = None

    if encoder_fn is None:
        # Fallback to HF Transformers mean pooling
        if torch is None:
            raise SystemExit(
                "Transformers/torch are required for this model. Install: pip install torch transformers"
            )
        device = "cuda" if torch.cuda.is_available() else "cpu"
        tok = AutoTokenizer.from_pretrained(args.model)
        hf_model = AutoModel.from_pretrained(args.model).to(device)
        backend = "transformers"

        def encoder_fn(texts):
            enc = tok(
                list(texts),
                padding=True,
                truncation=True,
                max_length=128,
                return_tensors="pt",
            ).to(device)
            with torch.no_grad():
                out = hf_model(**enc)
                hidden = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]
                mask = enc["attention_mask"].unsqueeze(-1)
                masked = hidden * mask
                summed = masked.sum(dim=1)
                count = mask.sum(dim=1).clamp(min=1)
                pooled = summed / count
                Z = pooled.cpu().numpy()
                if args.metric == "cosine":
                    norms = np.linalg.norm(Z, axis=1, keepdims=True) + 1e-12
                    Z = Z / norms
                return Z

    print(f"Backend: {backend}")

    chunk_cols = [f"chunk{i}" for i in range(1, k + 1)]
    tokens = build_vocab(df, chunk_cols)
    print(f"Unique tokens: {len(tokens):,}")
    # Encode in batches via encoder_fn
    emb = {}
    for i in tqdm(range(0, len(tokens), args.batch_size), desc="Encoding vocab"):
        batch = tokens[i : i + args.batch_size]
        Z = encoder_fn(batch)
        emb.update(zip(batch, Z))

    # Helper accessors
    def vec(x: str | float | None) -> np.ndarray | None:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return None
        return emb.get(str(x))

    def logf(x: str | float | None) -> float:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return float("nan")
        return float(freq.get(str(x).lower(), float("nan")))

    dist = d_cosine if args.metric == "cosine" else d_euclid

    # Build dynamic column names for chosen metric
    metric_prefix = "cosine" if args.metric == "cosine" else "euclidean"

    # Columns for the chosen k
    pair_cols: List[str] = []
    for i, j in combinations(range(1, k + 1), 2):
        pair_cols.append(f"{metric_prefix}_distance_chunk{i}_and_chunk{j}")
    corpus_cols = [f"{metric_prefix}_corpus_and_chunk{i}" for i in range(1, k + 1)]
    concat_col = f"{metric_prefix}_corpus_and_all_chunks"

    out_cols = (
        ["count_of_chunks", "corpus", *chunk_cols]
        + pair_cols
        + corpus_cols
        + [concat_col]
        + ["length_corpus"]
        + [f"length_chunk{i}" for i in range(1, k + 1)]
        + ["logfreq_corpus"]
        + [f"logfreq_chunk{i}" for i in range(1, k + 1)]
    )

    rows: List[List[object]] = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="Enriching rows"):
        corpus = r["corpus"]
        chunks = [r.get(c) for c in chunk_cols]
        present_mask = [isinstance(c, str) and len(c) > 0 and c.lower() != "nan" for c in chunks]

        v_c = vec(corpus)
        v_chunks = [vec(c if m else None) for c, m in zip(chunks, present_mask)]

        # Pairwise distances
        pair_vals: List[float] = []
        for (i, j) in combinations(range(k), 2):
            vi, vj = v_chunks[i], v_chunks[j]
            pair_vals.append(dist(vi, vj))

        # Corpus vs chunk distances
        corpus_vals = [dist(v_c, vc) for vc in v_chunks]

        # Corpus vs concatenated chunks
        present_chunks = [c for c, m in zip(chunks, present_mask) if m]
        concat_chunks = " ".join(present_chunks)
        if concat_chunks in emb:
            v_concat = emb[concat_chunks]
        else:
            # Compute embedding on the fly if not in vocab
            v_concat_arr = encoder_fn([concat_chunks])
            v_concat = v_concat_arr[0]
            if args.metric == "cosine":
                norm = np.linalg.norm(v_concat) + 1e-12
                v_concat = v_concat / norm
            emb[concat_chunks] = v_concat
        concat_val = dist(v_c, v_concat)

        # Lengths
        length_corpus = len(str(corpus)) if isinstance(corpus, str) and len(corpus) > 0 else float("nan")
        length_chunks = [len(c) if isinstance(c, str) and len(c) > 0 else float("nan") for c in chunks]

        # Log frequencies
        logf_corpus = logf(corpus)
        logf_chunks = [logf(c if m else None) for c, m in zip(chunks, present_mask)]

        row = [
            int(r["count_of_chunks"]),
            str(corpus) if isinstance(corpus, str) and len(corpus) > 0 else float("nan"),
            *(str(c) if isinstance(c, str) and len(c) > 0 else float("nan") for c in chunks),
            *pair_vals,
            *corpus_vals,
            concat_val,
            length_corpus,
            *length_chunks,
            logf_corpus,
            *logf_chunks,
        ]
        rows.append(row)

    out = pd.DataFrame(rows, columns=out_cols)
    out.to_csv(args.output, index=False)
    print(f"Saved enriched data: {args.output} (rows: {len(out)})")


if __name__ == "__main__":
    main()
