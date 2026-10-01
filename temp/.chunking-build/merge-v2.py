"""기존 패키지를 유지하고 세 번째 슬라이드와 발표자 노트만 교체함."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json

folder = Path(__file__).parent
source = folder.parent / "chunking_design_best_practices.pptx"
draft = folder / "draft-v2.pptx"
target = folder / "candidate-v2.pptx"
with ZipFile(source) as package:
    original = {name: package.read(name) for name in package.namelist()}
with ZipFile(draft) as package:
    authored = {name: package.read(name) for name in package.namelist()}
for name in ("ppt/slides/_rels/slide3.xml.rels", "ppt/notesSlides/_rels/notesSlide3.xml.rels"):
    assert original[name] == authored[name], f"슬라이드 관계 검토 필요: {name}"
changed = ["ppt/slides/slide3.xml", "ppt/notesSlides/notesSlide3.xml"]
final = dict(original)
for name in changed:
    final[name] = authored[name]
with ZipFile(target, "w", ZIP_DEFLATED) as package:
    for name, data in final.items():
        package.writestr(name, data)
assert all(final[name] == data for name, data in original.items() if name not in changed)
print(json.dumps({"modified_parts": changed, "other_parts_unchanged": True}))
