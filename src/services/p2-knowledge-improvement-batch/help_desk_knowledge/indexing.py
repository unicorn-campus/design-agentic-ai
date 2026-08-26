from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Sequence

import tiktoken
from openai import OpenAI
from pypdf import PdfReader

from .specs import RagSpec


class ScannedDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedSection:
    source_uri: str
    source_location: str
    text: str


@dataclass(frozen=True)
class IndexedChunk:
    chunk_id: str
    document_id: str
    content: str
    source_uri: str
    source_location: str
    embedding: Sequence[float]


class _HtmlMarkdownParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.in_cell = False
        self.cell_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"p", "div", "br"}:
            self.parts.append("\n\n")
        elif tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append(f"\n\n{'#' * int(tag[1])} ")
        elif tag in {"td", "th"}:
            self.in_cell = True
            self.cell_text = []
        elif tag == "tr":
            self.parts.append("\n|")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"}:
            self.parts.append(" " + " ".join(self.cell_text).strip() + " |")
            self.in_cell = False
        elif tag == "table":
            self.parts.append("\n\n")

    def handle_data(self, data: str) -> None:
        if self.in_cell:
            self.cell_text.append(data)
        else:
            self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def extract_sections(path: Path) -> tuple[ExtractedSection, ...]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(path)
        sections = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text(extraction_mode="layout") or "").strip()
            if not text and len(page.images) > 0:
                raise ScannedDocumentError(f"OCR 미사용 스캔 문서 격리: {path.name} {page_number}쪽")
            if text:
                sections.append(ExtractedSection(path.as_uri(), f"page={page_number}", text))
        return tuple(sections)
    if suffix in {".html", ".htm"}:
        parser = _HtmlMarkdownParser()
        parser.feed(path.read_text(encoding="utf-8"))
        return (ExtractedSection(path.as_uri(), "html", parser.text()),)
    raise ValueError(f"지원하지 않는 승인 문서 형식: {suffix}")


SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"\b\d{6}-?\d{7}\b"),
    re.compile(r"(?i)\b(?:cvc|password|auth[_ -]?token)\s*[:=]\s*\S+"),
)


def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(line for line in lines if line and not re.fullmatch(r"\d+", line))
    for pattern in SENSITIVE_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    return cleaned.strip()


def chunk_section(section: ExtractedSection, spec: RagSpec) -> tuple[tuple[str, str], ...]:
    encoding = tiktoken.encoding_for_model(spec.embedding_model)
    tokens = encoding.encode(clean_text(section.text))
    if spec.overlap_tokens >= spec.chunk_tokens:
        raise ValueError("청크 중첩은 청크 크기보다 작아야 함")
    chunks = []
    step = spec.chunk_tokens - spec.overlap_tokens
    for start in range(0, len(tokens), step):
        chunk_tokens = tokens[start : start + spec.chunk_tokens]
        if not chunk_tokens:
            break
        chunks.append((f"{section.source_location}:token={start}", encoding.decode(chunk_tokens)))
        if start + spec.chunk_tokens >= len(tokens):
            break
    return tuple(chunks)


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str) -> None:
        self._client = OpenAI(api_key=api_key)

    def embed_query(self, text: str, *, model: str, dimensions: int) -> Sequence[float]:
        response = self._client.embeddings.create(
            model=model,
            input=text,
            dimensions=dimensions,
        )
        return response.data[0].embedding

    def embed_documents(
        self,
        texts: Sequence[str],
        *,
        model: str,
        dimensions: int,
    ) -> tuple[Sequence[float], ...]:
        response = self._client.embeddings.create(
            model=model,
            input=list(texts),
            dimensions=dimensions,
        )
        return tuple(item.embedding for item in response.data)


def build_chunks(
    paths: Iterable[Path],
    spec: RagSpec,
    embedding_client: OpenAIEmbeddingClient,
) -> tuple[IndexedChunk, ...]:
    pending: list[tuple[str, str, str, str, str]] = []
    for path in paths:
        document_id = hashlib.sha256(path.as_uri().encode()).hexdigest()
        for section in extract_sections(path):
            for location, content in chunk_section(section, spec):
                chunk_id = hashlib.sha256(
                    f"{document_id}:{location}:{content}".encode()
                ).hexdigest()
                pending.append((chunk_id, document_id, section.source_uri, location, content))
    embeddings = embedding_client.embed_documents(
        [item[4] for item in pending],
        model=spec.embedding_model,
        dimensions=spec.embedding_dimensions,
    )
    return tuple(
        IndexedChunk(
            chunk_id=item[0],
            document_id=item[1],
            source_uri=item[2],
            source_location=item[3],
            content=item[4],
            embedding=embedding,
        )
        for item, embedding in zip(pending, embeddings, strict=True)
    )
