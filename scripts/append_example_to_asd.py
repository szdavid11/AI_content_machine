import json
from pathlib import Path

nb_path = Path('word_jokes/asd.ipynb')
nb = json.loads(nb_path.read_text(encoding='utf-8'))

cells = nb.get('cells', [])

# Detect if the example is already present
already = any(
    c.get('cell_type') == 'markdown' and any('English–Hungarian translate() example' in (ln or '') for ln in c.get('source', []))
    for c in cells
)

if not already:
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## English–Hungarian translate() example\n",
            "Uses FreeDict hun↔eng dictionary. First call may download and index."
        ],
    })

    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "from word_jokes.eh_translator import translate\n",
            "for w in ['kutya','macska','számítógép','dog','house','computer']:\n",
            "    print(w, '->', translate(w))\n",
        ],
    })

    nb['cells'] = cells
    nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding='utf-8')
    print('Appended example cells to', nb_path)
else:
    print('Example already present; no changes made.')

