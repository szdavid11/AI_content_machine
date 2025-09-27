import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from word_jokes.eh_translator import _build_indexes, TEI_PATH

idx = _build_indexes(TEI_PATH)
print('hun_to_eng size:', len(idx['hun_to_eng']))
print('eng_to_hun size:', len(idx['eng_to_hun']))
for key in ['kutya', 'macska', 'számítógép']:
    print(key, '->', idx['hun_to_eng'].get(key.casefold()))
for key in ['dog', 'cat', 'computer']:
    print(key, '->', idx['eng_to_hun'].get(key.casefold()))
