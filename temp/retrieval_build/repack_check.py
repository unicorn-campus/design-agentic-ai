"""pptxgenjs 산출물을 OPC 규칙에 맞게 다시 묶고 구조를 검사함.

빈 폴더 항목을 빼고 [Content_Types].xml을 맨 앞에 두는 이유:
PowerPoint가 패키지를 읽을 때 폴더 항목·순서 문제로 "복구 필요"를 띄우는 경우를 피하기 위함.
"""
import re
import sys
import zipfile
from xml.dom import minidom

src = sys.argv[1]
tmp = src + ".tmp"

with zipfile.ZipFile(src) as zin:
    names = [n for n in zin.namelist() if not n.endswith("/")]
    names.sort(key=lambda n: (n != "[Content_Types].xml", n))
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, zin.read(n))

import os
os.replace(tmp, src)

problems = []
with zipfile.ZipFile(src) as z:
    names = z.namelist()
    if any(n.endswith("/") for n in names):
        problems.append("폴더 항목 남음")
    ct = z.read("[Content_Types].xml").decode("utf-8")
    defaults = set(re.findall(r'Default Extension="(\w+)"', ct))
    overrides = set(re.findall(r'Override PartName="([^"]+)"', ct))
    for n in names:
        if n == "[Content_Types].xml":
            continue
        ext = n.rsplit(".", 1)[-1]
        if "/" + n not in overrides and ext not in defaults:
            problems.append(f"콘텐츠 형식 미등록: {n}")
        if n.endswith((".xml", ".rels")):
            data = z.read(n).decode("utf-8")
            try:
                minidom.parseString(data.encode("utf-8"))
            except Exception as e:  # 잘못된 XML은 PowerPoint 복구 창의 대표 원인
                problems.append(f"XML 오류 {n}: {e}")
            if n.startswith("ppt/slides/slide"):
                if re.search(r'prst="(?:rect|ellipse|line|rightArrow)"><a:avLst><a:gd', data):
                    problems.append(f"둥글기 값이 붙은 비둥근 도형: {n}")
                for v in re.findall(r'prst="roundRect"><a:avLst><a:gd name="adj" fmla="val (\d+)"', data):
                    if int(v) > 50000:
                        problems.append(f"roundRect adj 범위 초과 {v}: {n}")
                if re.search(r'"(?:undefined|NaN|null)"', data):
                    problems.append(f"undefined/NaN 값: {n}")
    for n in names:
        if n.endswith(".rels"):
            base = n.replace("_rels/", "").replace(".rels", "")
            folder = base.rsplit("/", 1)[0] if "/" in base else ""
            for tgt, mode in re.findall(r'Target="([^"]+)"(?: TargetMode="(\w+)")?', z.read(n).decode("utf-8")):
                if mode == "External":
                    continue
                path = os.path.normpath(os.path.join(folder, tgt)).replace("\\", "/").lstrip("/")
                if tgt.startswith("/"):
                    path = tgt.lstrip("/")
                if path not in names:
                    problems.append(f"끊긴 관계 {n} → {tgt}")

print("파일 수:", len(names))
print("문제:", problems if problems else "없음")
sys.exit(1 if problems else 0)
