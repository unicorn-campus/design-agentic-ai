import json, re, hashlib, posixpath
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parent
source = Path('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx')
ns = {'a':'http://schemas.openxmlformats.org/drawingml/2006/main', 'p':'http://schemas.openxmlformats.org/presentationml/2006/main', 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
norm = lambda value: re.sub(r'\s+', '', value)
def images(z, n):
    slide = ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
    rels = {r.get('Id'):r.get('Target') for r in ET.fromstring(z.read(f'ppt/slides/_rels/slide{n}.xml.rels'))}
    result = []
    for blip in slide.findall('.//a:blip', ns):
        target = rels[blip.get('{'+ns['r']+'}embed')]
        path = target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/slides/'+target)
        result.append(hashlib.sha256(z.read(path)).hexdigest())
    return result
with ZipFile(source) as old, ZipFile(root/'candidate-v2.pptx') as new:
    slides = [ET.fromstring(new.read(f'ppt/slides/slide{n}.xml')) for n in range(1,56)]
    all_text = norm(''.join(t.text or '' for slide in slides for t in slide.findall('.//a:t', ns)))
    checks = []
    for a,b in [(4,4),(9,24)]:
        assert images(old,a) and images(old,a)==images(new,b), ('workflow changed',a,b)
        checks.append({'original':a,'revised':b,'image_sha256_match':True})
    shapes = json.loads((root/'original-shapes.json').read_text(encoding='utf8'))
    full = [(5,23),(5,26),(6,16),(6,18),(6,27),(6,31),(7,9),(8,9),(8,17),(10,12),(10,16),(11,31),(11,34),(11,50),(12,31),(14,10)]
    for page, sid in full:
        value=next(x['text'] for x in shapes if x['slide']==page and x['id']==str(sid))
        assert norm(value) in all_text, ('missing original code',page,sid)
    snippets = ['self._model = SentenceTransformer(self.model_name, device=self.device)', 'self._store = Chroma(', 'collection_configuration={"hnsw": {"space": "cosine"}}', 'self._model = CrossEncoder(self.model_name, max_length=self.max_length)', 'raw = model.predict(', 'activation_fn=torch.nn.Sigmoid()', 'runnable = model.with_structured_output(schema, **kwargs)', 'output = runnable.invoke([("system", system), ("human", user)])']
    for snippet in snippets:
        assert norm(snippet) in all_text, ('missing code',snippet)
    owners=[i+1 for i,s in enumerate(slides) if s.findall('.//a:tbl', ns)]
    mapping=json.loads((root/'v2-page-map.json').read_text(encoding='utf8'))
    for i,m in enumerate(mapping):
        if m['kind']=='detail':
            content=norm(''.join(t.text or '' for t in slides[i].findall('.//a:t',ns)))
            assert norm(m['title']) in content, ('node title missing',i+1)
    report={'slide_count':len(slides),'workflow_images':checks,'original_complete_code_blocks':len(full),'additional_core_snippets':len(snippets),'native_table_slides':owners,'node_count':len(set((m['part'],m['node']) for m in mapping if m['kind']=='detail'))}
    (root/'preservation-v2.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
