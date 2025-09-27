import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from word_jokes.eh_translator import _iter_entries, _split_translations, TEI_PATH
from xml.etree import ElementTree as ET

ns = {"tei": "http://www.tei-c.org/ns/1.0"}

count = 0
with_trans = 0
for e in _iter_entries(TEI_PATH):
    count += 1
    hws = [o.text for o in e.findall('./tei:form/tei:orth', ns) or e.findall('./tei:orth', ns) if o.text]
    trans = []
    for sense in e.findall('.//tei:sense', ns):
        for cit in sense.findall('./tei:cit', ns):
            if cit.get('type') != 'trans':
                continue
            q = cit.find('./tei:quote', ns)
            if q is not None and q.text:
                trans.extend(_split_translations(q.text))
    if trans and hws:
        with_trans += 1
        print('HW:', hws[:2], 'TRANS:', trans[:4])
        if with_trans >= 5:
            break

print('count entries seen:', count)
print('with head + trans:', with_trans)

