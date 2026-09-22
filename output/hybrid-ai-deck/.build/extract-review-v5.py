from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import json

p=Path(__file__).resolve().parent
source=p.parent/'final/신한카드 하이브리드AI_v4_47페이지수정.pptx'
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
def text(el):
    return '\n'.join(''.join(t.text or '' for t in para.findall('.//a:t',ns)) for para in el.findall('.//a:p',ns))
pages=[]
with ZipFile(source) as z:
    for n in range(1,56):
        slide=ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
        shapes=[]
        for s in slide.findall('.//p:sp',ns):
            c=s.find('.//p:cNvPr',ns)
            shapes.append({'id':c.get('id'),'name':c.get('name'),'text':text(s)})
        tables=[]
        for t in slide.findall('.//a:tbl',ns):
            tables.append([[text(c) for c in r.findall('a:tc',ns)] for r in t.findall('a:tr',ns)])
        pages.append({'page':n,'shapes':shapes,'tables':tables,'notes':text(ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{n}.xml')))})
(p/'review-v4-content.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf8')
print('Extracted 55 slides for source audit')
