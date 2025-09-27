import sys
from xml.etree import ElementTree as ET

tei_path = sys.argv[1]
ns = {"tei": "http://www.tei-c.org/ns/1.0"}

cnt_entries = 0
cnt_with_trans = 0
examples = 0
for event, elem in ET.iterparse(tei_path, events=("end",)):
    if elem.tag != f"{{{ns['tei']}}}entry":
        continue
    cnt_entries += 1
    hws = [o.text for o in elem.findall("./tei:form/tei:orth", ns) or elem.findall("./tei:orth", ns) if o.text]
    trans = []
    for sense in elem.findall(".//tei:sense", ns):
        for cit in sense.findall("./tei:cit", ns):
            if cit.get("type") != "trans":
                continue
            q = cit.find("./tei:quote", ns)
            if q is not None and q.text:
                trans.append(q.text.strip())
    if trans:
        cnt_with_trans += 1
        if examples < 5:
            print("ENTRY:", ", ".join(hws[:3]))
            print("TRANS:", trans[:5])
            print("---")
            examples += 1
    elem.clear()

print("entries:", cnt_entries)
print("with_en_trans:", cnt_with_trans)
