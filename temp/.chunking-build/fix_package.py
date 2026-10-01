"""PptxGenJS가 생성한 존재하지 않는 마스터의 콘텐츠 타입 선언만 제거함."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import xml.etree.ElementTree as ET

target = Path(__file__).with_name("candidate.pptx")
with ZipFile(target) as package:
    files = {name: package.read(name) for name in package.namelist()}
namespace = "http://schemas.openxmlformats.org/package/2006/content-types"
ET.register_namespace("", namespace)
root = ET.fromstring(files["[Content_Types].xml"])
removed = []
for item in list(root):
    part = item.get("PartName", "").lstrip("/")
    if part.startswith("ppt/slideMasters/") and part not in files:
        removed.append(part)
        root.remove(item)
files["[Content_Types].xml"] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
with ZipFile(target, "w", ZIP_DEFLATED) as package:
    for name, content in files.items():
        package.writestr(name, content)
print({"removed_orphan_master_declarations": removed})
