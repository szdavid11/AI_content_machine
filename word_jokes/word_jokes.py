import pandas as pd
from itertools import permutations, combinations, batched
import random
import numpy as np

import time
from typing import Iterable, Sequence, Union


def get_corpus():
    # Read CSV with error handling for problematic lines
    df = pd.read_csv('words_hu.csv', on_bad_lines='skip', dtype=str)

    # Remove common prefixes
    prefix_pattern = '^(meg|át|fel|el|be|ki|elő|le|vissza|oda|ide|túl|körül|kör|felül|alul|kívül|belül|hátul|elől|hátra|előre|össze|szét|újra|felre|alá|oldal)'
    
    # Filter out rows where szavak is NaN and doesn't start with prefixes
    df = df[
        df['szavak'].notna() & 
        (df['szavak'].str.contains(prefix_pattern, regex=True, na=False) == False)
    ]

    # Drop duplicates
    df = df.drop_duplicates(subset=['szavak'])

    df = df[df['szavak'].str.len() > 1]

    CORPUS = df['szavak'].values
    random.shuffle(CORPUS)

    return CORPUS

def save_valid_combos(combo_batch, max_size=14):
    df_combo = pd.DataFrame(combo_batch)
    comb_len_sum = df_combo[0].str.len() + df_combo[1].str.len() + df_combo[2].str.len()
    df_combo = df_combo[comb_len_sum < max_size]

    df_perms = pd.concat(
        [df_combo.rename(columns=dict(zip(indexes, columns)), inplace=False)
        for indexes in permutation_indexes], ignore_index=True
    )
    df_perms['word'] = df_perms.sum(axis=1)
    df_good = df_perms[df_perms['word'].isin(corpus_long_words)]
    valid_findings = len(df_good)
    if valid_findings:
        print('Count of new findings', valid_findings)
        df_good.to_csv('valid_combinations.csv', mode='a', header=False, index=False)


if __name__ == "__main__":
    corpus = get_corpus()
    corpus_short_words = corpus[ pd.Series(corpus).str.len() <= 6]
    print("Short words", len(corpus_short_words))
    max_size = 14
    corpus_long_words = corpus[
        (pd.Series(corpus).str.len() >= 7) &
        (pd.Series(corpus).str.len() < max_size) 
    ]
    print("Long words", len(corpus_long_words))

    columns = [0,1,2]
    permutation_indexes = list(permutations(columns))

    start = time.time()
    for i, combo_batch in enumerate(batched(combinations(corpus_short_words, 3), 50_000_000)):
        print(f'Iter {i}, elapsed time: {int(time.time() - start)} sec')
        save_valid_combos(combo_batch, max_size)