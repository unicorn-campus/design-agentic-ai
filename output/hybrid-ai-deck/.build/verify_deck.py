import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

root=Path(__file__).resolve().parent
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
mapping=json.loads((root/'page-map.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(root/'candidate.pptx') as z:
    slides=sorted([x for x in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',x)],key=lambda x:int(re.search(r'slide(\d+)',x)[1]))
    assert len(slides)==30
    for i,name in enumerate(slides):
        e=ET.fromstring(z.read(name))
        pictures=len(e.findall('.//p:pic',ns));shapes=len(e.findall('.//p:sp',ns));edges=len(e.findall('.//p:cxnSp',ns));tables=len(e.findall('.//a:tbl',ns))
        if mapping[i]['edited']: assert pictures==0,(i+1,pictures)
        print(i+1,'original',mapping[i]['source'],'shapes',shapes,'connectors',edges,'tables',tables,'pictures',pictures)
    for n in [4,13,14]:
        e=ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
        assert len(e.findall('.//p:cxnSp',ns))>0
    notes=[n for n in z.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',n)]
    for n in notes:
        text=' '.join(ET.fromstring(z.read(n)).itertext())
        assert 'undefined' not in text,(n,text)
    print('PASS: 30 slides; native editable diagrams; no images on rebuilt slides; notes valid')
