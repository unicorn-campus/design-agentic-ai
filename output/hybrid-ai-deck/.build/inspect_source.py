from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as E
import json

src = Path(r'C:\Users\hiond\Documents\강의\신한카드\신한카드 하이브리드AI.pptx')
out = Path(__file__).parent
ns = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
with ZipFile(src) as z:
    pres=E.fromstring(z.read('ppt/presentation.xml'))
    rel={x.attrib['Id']:x.attrib['Target'] for x in E.fromstring(z.read('ppt/_rels/presentation.xml.rels'))}
    print('SIZE',pres.find('p:sldSz',ns).attrib)
    result=[]
    for i,sl in enumerate(pres.find('p:sldIdLst',ns),1):
        target=rel[sl.attrib['{'+ns['r']+'}id']]
        p='ppt/'+target.lstrip('/') if not target.startswith('/') else target[1:]
        root=E.fromstring(z.read(p))
        texts=[''.join(n.itertext()) for n in root.findall('.//a:t',ns)]
        pics=root.findall('.//p:pic',ns)
        result.append({'slide':i,'path':p,'texts':texts,'pictures':len(pics)})
        print(i, 'PICS',len(pics), '\n'+'\n'.join(texts))
    (out/'source_content.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for name in z.namelist():
        if name.startswith('ppt/media/'):
            p=out/'source_media'/Path(name).name
            p.parent.mkdir(exist_ok=True)
            p.write_bytes(z.read(name))
