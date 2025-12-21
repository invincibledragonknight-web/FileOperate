"""
Utilities for file inventory, extraction, OCR placeholders, and safe mapping execution.
"""

from __future__ import annotations

import base64
import hashlib
import mimetypes
import os
import shutil
import zipfile
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Iterable, List, Tuple

import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from pdf2image import convert_from_path
from PIL import Image
from pypdf import PdfReader


def env_paths() -> dict:
    base_dir = Path(__file__).resolve().parents[2]
    work_root = os.getenv(
        "DEEP_SCHOLAR_WORK_ROOT",
        str(base_dir / "data" / "work"),
    )
    work_root_path = Path(work_root)
    return {
        "work": str(work_root_path),
        "upload": str(work_root_path / "uploads"),
        "raw": str(work_root_path / "raw"),
        "output": str(work_root_path / "output"),
        "db": str(work_root_path / "db"),
        "embed_base": os.getenv(
            "DEEP_SCHOLAR_EMBEDDING_BASE_URL", "http://127.0.0.1:8081/v1"
        ),
        "embed_key": os.getenv("DEEP_SCHOLAR_EMBEDDING_API_KEY", ""),
        "embed_model": os.getenv("DEEP_SCHOLAR_EMBEDDING_MODEL", "qwen3-embed"),
        "vlm_base": os.getenv("DEEP_SCHOLAR_VLM_BASE_URL", ""),
        "vlm_key": os.getenv("DEEP_SCHOLAR_VLM_API_KEY", ""),
        "vlm_model": os.getenv("DEEP_SCHOLAR_VLM_MODEL", "qwen3-vl"),
    }


def ensure_dirs(*paths: str) -> None:
    for p in paths:
        Path(p).mkdir(parents=True, exist_ok=True)


def list_upload_files() -> List[dict]:
    cfg = env_paths()
    ensure_dirs(cfg["upload"])
    upload_dir = Path(cfg["upload"])
    files = []
    for p in sorted(upload_dir.rglob("*"), key=lambda item: str(item)):
        if not p.is_file():
            continue
        stat = p.stat()
        mime_type, _ = mimetypes.guess_type(str(p))
        files.append(
            {
                "name": p.name,
                "path": str(p),
                "relative_path": str(p.relative_to(upload_dir)),
                "suffix": p.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_utc": datetime.utcfromtimestamp(stat.st_mtime).isoformat()
                + "Z",
                "mime_type": mime_type or "application/octet-stream",
            }
        )
    return files


def unpack_zip_archive(
    src: Path,
    destination_root: str,
    allow_overwrite: bool = False,
    max_listed: int = 200,
) -> dict:
    if not src.exists():
        return {"errors": [f"File not found: {src}"]}
    if not zipfile.is_zipfile(src):
        return {"errors": [f"Not a zip archive: {src}"]}

    dest_root = Path(destination_root)
    ensure_dirs(str(dest_root))
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest_dir = dest_root / "__unpacked__" / f"{src.stem}__{timestamp}"
    dest_dir.mkdir(parents=True, exist_ok=True)

    extracted: List[dict] = []
    skipped: List[dict] = []
    extracted_total = 0

    try:
        with zipfile.ZipFile(src) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                rel_path = Path(info.filename)
                if rel_path.is_absolute() or ".." in rel_path.parts:
                    skipped.append(
                        {
                            "path": info.filename,
                            "reason": "unsafe path",
                        }
                    )
                    continue

                target_path = dest_dir / rel_path
                target_path.parent.mkdir(parents=True, exist_ok=True)

                if target_path.exists() and not allow_overwrite:
                    skipped.append(
                        {
                            "path": str(target_path),
                            "reason": "destination exists",
                        }
                    )
                    continue

                with archive.open(info) as source, target_path.open("wb") as dest:
                    shutil.copyfileobj(source, dest)

                extracted_total += 1
                if len(extracted) < max_listed:
                    extracted.append(
                        {
                            "path": str(target_path),
                            "size_bytes": info.file_size,
                        }
                    )
    except (zipfile.BadZipFile, RuntimeError) as exc:
        return {"errors": [str(exc)], "destination": str(dest_dir), "source": str(src)}

    return {
        "source": str(src),
        "destination": str(dest_dir),
        "extracted_total": extracted_total,
        "extracted_listed": extracted,
        "skipped_total": len(skipped),
        "skipped": skipped,
    }


def read_text_file(path: Path, max_chars: int = 200000) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > max_chars:
        return text[:max_chars]
    return text


def get_file_hash(path: Path, algorithm: str = "sha256") -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_vector_store(db_root: str, embeddings: OpenAIEmbeddings) -> FAISS:
    index_dir = Path(db_root) / "faiss_index"
    if index_dir.exists():
        return FAISS.load_local(
            str(index_dir),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    sample_dim = len(embeddings.embed_query("bootstrap"))
    index = faiss.IndexFlatL2(sample_dim)
    return FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )


def save_vector_store(store: FAISS, db_root: str) -> str:
    index_dir = Path(db_root) / "faiss_index"
    index_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(index_dir))
    return str(index_dir)


def extract_pdf_text(path: Path) -> str:
    text_parts: List[str] = []
    reader = PdfReader(str(path))
    for page in reader.pages:
        txt = page.extract_text() or ""
        if txt.strip():
            text_parts.append(txt)
    return "\n\n".join(text_parts).strip()


def needs_ocr(text: str, min_chars: int = 200) -> bool:
    return len(text) < min_chars


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> Iterable[str]:
    words = text.split()
    chunk: List[str] = []
    count = 0
    for word in words:
        chunk.append(word)
        count += len(word) + 1
        if count >= chunk_size:
            yield " ".join(chunk)
            chunk = chunk[-overlap:] if overlap else []
            count = len(" ".join(chunk))
    if chunk:
        yield " ".join(chunk)


def move_to_raw(src: Path, raw_root: str) -> Path:
    now = datetime.utcnow()
    ext = src.suffix.lower().lstrip(".") or "file"
    dest_dir = Path(raw_root) / str(now.year) / f"{now.month:02d}" / ext
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = src.stem.replace(" ", "_")
    dest_name = f"{safe_stem}__{now.strftime('%Y%m%d_%H%M%S')}{src.suffix}"
    dest_path = dest_dir / dest_name
    shutil.move(str(src), dest_path)
    return dest_path


OCR_SYSTEM_PROMPT = (
    "You are an OCR engine. Extract ALL visible text faithfully. "
    "Do NOT summarize. Do NOT interpret. Preserve numbers, dates, "
    "currency symbols, and line breaks."
)


def build_vlm_client(cfg: dict) -> ChatOpenAI | None:
    base_url = cfg.get("vlm_base")
    if not base_url:
        return None
    return ChatOpenAI(
        base_url=base_url,
        api_key=cfg.get("vlm_key") or "",
        model=cfg.get("vlm_model") or "qwen3-vl",
        temperature=0.0,
        max_tokens=4096,
    )


def normalize_vlm_response(response: object) -> str:
    content = getattr(response, "content", "")
    if isinstance(content, list):
        parts: List[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts).strip()
    return str(content).strip()


def image_to_data_url(image: Image.Image) -> str:
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def image_path_to_data_url(path: Path) -> str:
    with Image.open(path) as image:
        image = image.convert("RGB")
        return image_to_data_url(image)


def invoke_vlm_ocr(client: ChatOpenAI, data_url: str) -> str:
    messages = [
        SystemMessage(content=OCR_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {"type": "text", "text": "Perform OCR on this image."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]
        ),
    ]
    response = client.invoke(messages)
    return normalize_vlm_response(response)


def vlm_ocr_image(path: Path, cfg: dict) -> str:
    client = build_vlm_client(cfg)
    if client is None:
        return "VLM endpoint not configured; set DEEP_SCHOLAR_VLM_BASE_URL."

    data_url = image_path_to_data_url(path)
    return invoke_vlm_ocr(client, data_url)


def vlm_ocr_pil_image(image: Image.Image, client: ChatOpenAI) -> str:
    data_url = image_to_data_url(image.convert("RGB"))
    return invoke_vlm_ocr(client, data_url)


def vlm_ocr_pdf(
    path: Path,
    cfg: dict,
    dpi: int = 200,
    max_pages: int | None = None,
) -> str:
    client = build_vlm_client(cfg)
    if client is None:
        return "VLM endpoint not configured; set DEEP_SCHOLAR_VLM_BASE_URL."

    try:
        pages = convert_from_path(str(path), dpi=dpi)
    except Exception as exc:
        return (
            f"OCR failed for {path.name}: {exc}. "
            "Ensure poppler is installed and in PATH."
        )

    if max_pages is not None:
        pages = pages[:max_pages]

    texts: List[str] = []
    for index, page in enumerate(pages, start=1):
        page_text = vlm_ocr_pil_image(page, client)
        texts.append(f"--- Page {index} ---\n{page_text}")

    return "\n\n".join(texts).strip()


def parse_mapping_entries(mapping: object) -> List[Tuple[str, str]]:
    if isinstance(mapping, dict):
        return [(str(k), str(v)) for k, v in mapping.items()]
    if isinstance(mapping, list):
        entries: List[Tuple[str, str]] = []
        for item in mapping:
            if not isinstance(item, dict):
                continue
            src = (
                item.get("source")
                or item.get("src")
                or item.get("from")
                or item.get("old")
            )
            dest = (
                item.get("destination")
                or item.get("dest")
                or item.get("to")
                or item.get("new")
            )
            if src and dest:
                entries.append((str(src), str(dest)))
        return entries
    return []


def prepare_file_mapping(
    mapping: object,
    source_root: str | None,
    destination_root: str | None,
) -> Tuple[List[dict], List[str]]:
    entries = parse_mapping_entries(mapping)
    if not entries:
        return [], ["Mapping is empty or invalid."]

    errors: List[str] = []
    actions: List[dict] = []
    seen_sources = set()
    seen_destinations = set()

    for raw_source, raw_destination in entries:
        src_path = Path(raw_source)
        if not src_path.is_absolute():
            if not source_root:
                errors.append(f"Source root required for {raw_source}")
                continue
            src_path = Path(source_root) / raw_source

        dest_path = Path(raw_destination)
        if not dest_path.is_absolute():
            if not destination_root:
                errors.append(f"Destination root required for {raw_destination}")
                continue
            dest_path = Path(destination_root) / raw_destination

        src_key = str(src_path.resolve(strict=False))
        dest_key = str(dest_path.resolve(strict=False))

        if src_key in seen_sources:
            errors.append(f"Duplicate source: {src_path}")
        if dest_key in seen_destinations:
            errors.append(f"Duplicate destination: {dest_path}")
        if not src_path.exists():
            errors.append(f"Source missing: {src_path}")

        seen_sources.add(src_key)
        seen_destinations.add(dest_key)
        actions.append(
            {
                "source": str(src_path),
                "destination": str(dest_path),
            }
        )

    return actions, errors


def execute_file_mapping(
    actions: List[dict],
    operation: str = "move",
    allow_overwrite: bool = False,
) -> List[str]:
    results: List[str] = []
    for action in actions:
        src_path = Path(action["source"])
        dest_path = Path(action["destination"])
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if dest_path.exists():
            if dest_path.is_dir():
                raise ValueError(f"Destination exists as directory: {dest_path}")
            if not allow_overwrite:
                raise FileExistsError(f"Destination exists: {dest_path}")
            dest_path.unlink()

        if operation == "copy":
            shutil.copy2(src_path, dest_path)
            results.append(f"COPIED {src_path} -> {dest_path}")
        else:
            shutil.move(str(src_path), dest_path)
            results.append(f"MOVED {src_path} -> {dest_path}")

    return results


def vectorize_text(text: str, source_path: str, cfg: dict) -> Tuple[int, str]:
    ensure_dirs(cfg["db"])
    embeddings = OpenAIEmbeddings(
        base_url=cfg["embed_base"],
        api_key=cfg["embed_key"],
        model=cfg["embed_model"],
    )
    store = load_vector_store(cfg["db"], embeddings)
    chunks = list(chunk_text(text))
    docs = [
        Document(
            page_content=chunk,
            metadata={
                "source": source_path,
                "origin": "upload",
            },
        )
        for chunk in chunks
    ]
    if docs:
        store.add_documents(docs)
        index_path = save_vector_store(store, cfg["db"])
        return len(docs), index_path
    return 0, ""
