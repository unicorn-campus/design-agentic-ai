from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import ast, hashlib, json, posixpath, textwrap

root=Path(__file__).resolve().parent
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def text(el):
    return '\n'.join(''.join(t.text or '' for t in para.findall('.//a:t',ns)) for para in el.findall('.//a:p',ns))
def assets(z,n):
    rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read(f'ppt/slides/_rels/slide{n}.xml.rels'))}
    s=ET.fromstring(z.read(f'ppt/slides/slide{n}.xml'))
    result=[]
    for b in s.findall('.//a:blip',ns):
        target=rels[b.get('{'+ns['r']+'}embed')]
        path=target.lstrip('/') if target.startswith('/') else posixpath.normpath('ppt/slides/'+target)
        result.append(hashlib.sha256(z.read(path)).hexdigest())
    return result

report={'slideCount':58,'protectedImages':{},'codeChecks':[],'tests':{'indexer':'32 passed','retriever':'42 passed, 4 subtests passed'},'limitations':['External LLM and live PowerPoint app not exercised','Empty caution prompt/validator mismatch documented; production code unchanged']}
with ZipFile(root/'candidate-v5-reviewed.pptx') as z, ZipFile(root.parent/'final/신한카드 하이브리드AI_v4_47페이지수정.pptx') as old:
    for n in (4,24):
        assert assets(z,n)==assets(old,n),(n,assets(z,n),assets(old,n))
        report['protectedImages'][n]=assets(z,n)
    with ZipFile('C:/Users/hiond/Documents/강의/신한카드/신한카드 하이브리드AI.pptx') as original:
        assert assets(z,4)==assets(original,4)
        assert assets(z,24)==assets(original,9)
        report['originalWorkflowImagePreservation']='pass: original pages 4 and 9'
    slides=[ET.fromstring(z.read(f'ppt/slides/slide{n}.xml')) for n in range(1,59)]
    alltext='\n'.join(text(s) for s in slides)
    for forbidden in ('콜론 생략','따옴표·태그 공백은 강의 표기','상담사 ID','원본 핵심 코드 출처: 페이지'):
        assert forbidden not in alltext,forbidden
    for x in json.loads((root/'v5-source-excerpts.json').read_text(encoding='utf8')):
        rendered=text(slides[x['page']-1])
        assert x['code'] in rendered,('not transcribed',x['page'])
        code=x['code']
        try:
            ast.parse(code)
        except SyntaxError:
            ast.parse('def fragment():\n'+textwrap.indent(code,'    '))
        report['codeChecks'].append({'page':x['page'],'file':x['file'],'ranges':x['ranges'],'syntax':'pass','transcription':'pass'})
    # Preserve the user-supplied function exactly, apart from class indentation.
    expected='''def _run_search_transformed(self, state: RetrieverState, **_kwargs: Any) -> dict[str, Any]:
    groups, warnings = [], []
    for query in state.get("transformed_queries", []):
        try:
            groups.append(self._search_one(query, state))
        except Exception as error:
            groups.append([])
            warnings.append(f"변환 질의 검색 실패: {type(error).__name__}")
    return {"transformed_hit_groups": groups, "warnings": warnings}'''
    assert expected in text(slides[38])
    assert '최종 Top-3: B → D → C' in text(slides[45])
    assert 'rerank_query_groups' not in text(ET.fromstring(z.read('ppt/notesSlides/notesSlide46.xml')))
    assert 'rerank_each_query_and_merge' in text(ET.fromstring(z.read('ppt/notesSlides/notesSlide46.xml')))
    assert all(abs(a-b)<1e-12 for a,b in [(0.9*.95+.1*.7,.925),(.9*.92,.828),(.9*.9,.81),(.1*.8,.08)])
    report['page46Arithmetic']='pass'
    pages=[]
    for n,s in enumerate(slides,1):
        pages.append({'page':n,'text':text(s),'notes':text(ET.fromstring(z.read(f'ppt/notesSlides/notesSlide{n}.xml')))})
    (root/'review-v5-content.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf8')
(root/'content-validation-v5.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
