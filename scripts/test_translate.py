import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from word_jokes import eh_translator as t

idx = t._load_or_build_indexes()
print('hun_to_eng size ->', len(idx['hun_to_eng']))
print('eng_to_hun size ->', len(idx['eng_to_hun']))

for w in ['kutya', 'macska', 'számítógép', 'house', 'dog', 'computer']:
    print(w, '->', t.translate(w))
