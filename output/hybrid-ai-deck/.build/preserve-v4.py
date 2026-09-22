from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import posixpath

p=Path(__file__).resolve().parent
source=p.parent/'final/신한카드 하이브리드AI_v3_39페이지수정.pptx'
def note_part(z):
    rels=ET.fromstring(z.read('ppt/slides/_rels/slide47.xml.rels'))
    target=next(r.get('Target') for r in rels if r.get('Type').endswith('/notesSlide'))
    return target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/slides/'+target)
with ZipFile(source) as old, ZipFile(p/'candidate-v4.pptx') as authored:
    updates={'ppt/slides/slide47.xml':authored.read('ppt/slides/slide47.xml'),note_part(old):authored.read(note_part(authored))}
    with ZipFile(p/'candidate-v4-preserved.pptx','w') as out:
        for item in old.infolist():
            out.writestr(item,updates.get(item.filename,old.read(item.filename)))
with ZipFile(source) as old, ZipFile(p/'candidate-v4-preserved.pptx') as new:
    changed=[name for name in old.namelist() if old.read(name)!=new.read(name)]
    assert set(changed)==set(updates),changed
    print('Only these parts changed:',changed)
