import json, zipfile
from pathlib import Path
from xml.etree import ElementTree as E
src=Path('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx')
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
rows=[]
with zipfile.ZipFile(src) as z:
    for n in [5,6,7,8,10,11,12,14]:
        e=E.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
        for s in e.findall('.//p:sp',ns):
            tag=s.find('p:nvSpPr/p:cNvPr',ns)
            paras=s.findall('p:txBody/a:p',ns)
            text='\n'.join(''.join(t.text or '' for t in p.findall('.//a:t',ns)) for p in paras)
            rows.append({'slide':n,'id':tag.get('id'),'name':tag.get('name'),'text':text})
Path(__file__).with_name('original-shapes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for r in rows:
    print(f"PAGE {r['slide']} SHAPE {r['id']} {r['name']}\n{r['text']}\n")
