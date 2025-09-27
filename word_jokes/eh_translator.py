import os
import re
import json
from typing import Dict, List, Optional

from xml.etree import ElementTree as ET


FREEDICT_SRC_URL = "https://download.freedict.org/dictionaries/hun-eng/0.4.1/freedict-hun-eng-0.4.1.src.tar.xz"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dicts")
TEI_PATH = os.path.join(DATA_DIR, "hun-eng.tei")
INDEX_PATH = os.path.join(DATA_DIR, "hun_eng_index.json")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _download_hun_eng_tei(dest_path: str = TEI_PATH) -> None:
    """Download and extract the FreeDict Hungarian–English TEI source file.

    Downloads the `.src.tar.xz` and extracts only `hun-eng/hun-eng.tei`.
    """
    import tarfile
    import io
    import urllib.request

    _ensure_data_dir()
    # Stream the xz tarball and extract the TEI member
    with urllib.request.urlopen(FREEDICT_SRC_URL) as resp:
        data = resp.read()
    # Open tar from memory to avoid writing the tarball
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:xz") as tf:
        member = tf.getmember("hun-eng/hun-eng.tei")
        with tf.extractfile(member) as fsrc, open(dest_path, "wb") as fdst:
            fdst.write(fsrc.read())


def _iter_entries(tei_path: str):
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    # Incremental parse to avoid loading whole 26MB tree in memory at once
    for event, elem in ET.iterparse(tei_path, events=("end",)):
        if elem.tag == f"{{{ns['tei']}}}entry":
            yield elem
            elem.clear()


def _split_translations(text: str) -> List[str]:
    """Heuristic split of translation strings into individual terms.

    Many entries separate synonyms by "," or ";". We split on those, but keep
    parentheses content attached to preceding token.
    """
    # Replace slashes with comma to split variants like "big/large"
    text = text.replace("/", ",")
    parts = re.split(r"[,;]\s+", text)
    cleaned = []
    for p in parts:
        p = p.strip()
        # Drop empty and markers like "(obs.)"
        if not p:
            continue
        cleaned.append(p)
    return cleaned or ([text.strip()] if text.strip() else [])


def _build_indexes(tei_path: str = TEI_PATH) -> Dict[str, Dict[str, List[str]]]:
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    hun_to_eng: Dict[str, List[str]] = {}
    eng_to_hun: Dict[str, List[str]] = {}

    for entry in _iter_entries(tei_path):
        # Headwords
        hws = []
        for orth in entry.findall("./tei:form/tei:orth", ns) or entry.findall("./tei:orth", ns):
            if orth.text:
                hws.append(orth.text.strip())
        if not hws:
            continue
        # Collect English translations under senses
        eng_trans: List[str] = []
        for sense in entry.findall(".//tei:sense", ns):
            for cit in sense.findall("./tei:cit", ns):
                if cit.get("type") != "trans":
                    continue
                q = cit.find("./tei:quote", ns)
                if q is not None and q.text:
                    eng_trans.extend(_split_translations(q.text))
        if not eng_trans:
            continue
        # Normalize
        eng_trans = [t.strip() for t in eng_trans if t and t.strip()]
        if not eng_trans:
            continue
        for hw in hws:
            key = hw.strip()
            key_ci = key.casefold()
            hun_to_eng.setdefault(key_ci, [])
            for t in eng_trans:
                if t not in hun_to_eng[key_ci]:
                    hun_to_eng[key_ci].append(t)
                # Reverse index
                t_ci = t.casefold()
                eng_to_hun.setdefault(t_ci, [])
                if key not in eng_to_hun[t_ci]:
                    eng_to_hun[t_ci].append(key)

    return {"hun_to_eng": hun_to_eng, "eng_to_hun": eng_to_hun}


def _load_or_build_indexes() -> Dict[str, Dict[str, List[str]]]:
    _ensure_data_dir()
    if os.path.exists(INDEX_PATH):
        with open(INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    if not os.path.exists(TEI_PATH):
        _download_hun_eng_tei(TEI_PATH)
    idx = _build_indexes(TEI_PATH)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    return idx


# Lazy global cache
_IDX: Optional[Dict[str, Dict[str, List[str]]]] = None


def _get_idx() -> Dict[str, Dict[str, List[str]]]:
    global _IDX
    if _IDX is None:
        _IDX = _load_or_build_indexes()
    return _IDX


def translate(word: str) -> Optional[List[str]]:
    """Translate a single word between Hungarian and English.

    - If `word` is a Hungarian headword (per FreeDict), returns English translations.
    - Else if `word` matches an English translation, returns Hungarian headwords.
    - Returns None if no match.
    """
    if not word or not word.strip():
        return None
    w_norm = word.strip()
    w_ci = w_norm.casefold()
    idx = _get_idx()
    hun_to_eng = idx["hun_to_eng"]
    eng_to_hun = idx["eng_to_hun"]

    if w_ci in hun_to_eng:
        return hun_to_eng[w_ci]
    if w_ci in eng_to_hun:
        return eng_to_hun[w_ci]
    return None


if __name__ == "__main__":
    # quick manual test
    for term in ["kutya", "macska", "house", "számítógép", "program"]:
        print(term, "->", translate(term))
