from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import posixpath

p=Path(__file__).resolve().parent
old=p.parent/'final/신한카드 하이브리드AI_워크플로우_노드별상세_v2.pptx'
def note_part(z):
    rel=ET.fromstring(z.read('ppt/slides/_rels/slide39.xml.rels'))
    target=next(r.get('Target') for r in rel if r.get('Type').endswith('/notesSlide'))
    return target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/slides/'+target)
with ZipFile(old) as src, ZipFile(p/'candidate-v3.pptx') as authored:
    before_note,after_note=note_part(src),note_part(authored)
    updates={'ppt/slides/slide39.xml':authored.read('ppt/slides/slide39.xml'),before_note:authored.read(after_note)}
    with ZipFile(p/'candidate-v3-preserved.pptx','w') as out:
        for item in src.infolist():
            out.writestr(item,updates.get(item.filename,src.read(item.filename)))
with ZipFile(old) as src, ZipFile(p/'candidate-v3-preserved.pptx') as out:
    changed=[n for n in src.namelist() if src.read(n)!=out.read(n)]
    assert set(changed)==set(updates),changed
    a={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
    slide=ET.fromstring(out.read('ppt/slides/slide39.xml'))
    texts=['\n'.join(''.join(t.text or '' for t in para.findall('.//a:t',a)) for para in shape.findall('.//a:p',a)) for shape in slide.findall('.//p:sp',a)]
    expected=(p/'v3-expected-code.txt').read_text(encoding='utf8')
    assert expected in texts,'User code not retained exactly'
    print('User code matches exactly. Changed package parts:',changed)
