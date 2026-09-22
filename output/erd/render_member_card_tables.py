"""Add a title to the field-free Mermaid ERD image."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "member-card-tables-raw.png"
TARGET = HERE / "member-card-tables.png"
FONT = Path(r"C:\Windows\Fonts\malgunbd.ttf")

diagram = Image.open(SOURCE).convert("RGB")
width, diagram_height = diagram.size
top = 86
image = Image.new("RGB", (width, top + diagram_height), "#ffffff")
image.paste(diagram, (0, top))

draw = ImageDraw.Draw(image)
title_font = ImageFont.truetype(FONT, 38)
draw.text((35, 19), "카드 데이터 ERD", fill="#17263d", font=title_font)

image.save(TARGET, optimize=True)
print(f"Saved {TARGET} ({width}x{image.height})")
