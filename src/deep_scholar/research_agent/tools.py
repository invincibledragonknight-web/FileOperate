"""File analysis and reconstruction tools."""

import json
from pathlib import Path
from typing import Literal

from langchain_core.tools import tool

from research_agent.ingestion import (
    env_paths,
    execute_file_mapping,
    extract_pdf_text,
    get_file_hash,
    list_upload_files,
    needs_ocr,
    prepare_file_mapping,
    read_text_file,
    unpack_zip_archive,
    vectorize_text,
    vlm_ocr_image,
    vlm_ocr_pdf,
)


@tool(parse_docstring=True)
def think_tool(reflection: str) -> str:
    """Reflect on progress and next steps.

    Args:
        reflection: Brief reflection on findings, gaps, and actions.

    Returns:
        Confirmation string noting the reflection was recorded.
    """
    return f"Reflection recorded: {reflection}"


@tool(parse_docstring=True)
def list_uploads() -> str:
    """List files available in the uploads area under the work root.

    Returns:
        JSON summary of pending uploads (recursive).
    """
    files = list_upload_files()
    payload = {"count": len(files), "files": files}
    return json.dumps(payload, indent=2)


@tool(parse_docstring=True)
def unpack_zip(
    path: str,
    destination_root: str | None = None,
    allow_overwrite: bool = False,
    max_listed: int = 200,
) -> str:
    """Unpack a ZIP archive into a safe subfolder.

    Args:
        path: Absolute path to the ZIP file.
        destination_root: Root directory to place the extracted folder (defaults to
            the uploads area under the work root).
        allow_overwrite: Whether to overwrite existing files in the destination.
        max_listed: Maximum extracted file entries to include in the output list.

    Returns:
        JSON summary including destination, extracted counts, and skips.
    """
    cfg = env_paths()
    zip_path = Path(path)
    destination_root = destination_root or cfg["upload"]
    payload = unpack_zip_archive(
        zip_path,
        destination_root=destination_root,
        allow_overwrite=allow_overwrite,
        max_listed=max_listed,
    )
    return json.dumps(payload, indent=2)


@tool(parse_docstring=True)
def read_text(path: str, max_chars: int = 200000) -> str:
    """Read a text file with UTF-8 fallback.

    Args:
        path: Absolute path to the file.
        max_chars: Maximum characters to return.

    Returns:
        File content (possibly truncated) or an error message.
    """
    target = Path(path)
    if not target.exists():
        return f"File not found: {path}"
    return read_text_file(target, max_chars=max_chars)


@tool(parse_docstring=True)
def extract_pdf(path: str) -> str:
    """Extract text from a PDF without OCR.

    Args:
        path: Absolute path to the PDF.

    Returns:
        Extracted text if present, otherwise a prompt to run ocr_pdf.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        return f"File not found: {path}"
    text = extract_pdf_text(pdf_path)
    if needs_ocr(text):
        return f"Text sparse; use ocr_pdf on {path}."
    return text


@tool(parse_docstring=True)
def ocr_pdf(path: str, dpi: int = 200, max_pages: int | None = None) -> str:
    """OCR a PDF using the configured VLM backend.

    Args:
        path: Absolute path to the PDF to OCR.
        dpi: Render DPI for PDF pages.
        max_pages: Optional page limit for large PDFs.

    Returns:
        OCR text extracted from the PDF.
    """
    cfg = env_paths()
    pdf_path = Path(path)
    if not pdf_path.exists():
        return f"File not found: {path}"
    return vlm_ocr_pdf(pdf_path, cfg, dpi=dpi, max_pages=max_pages)


@tool(parse_docstring=True)
def ocr_image(path: str) -> str:
    """OCR an image using the configured VLM backend.

    Args:
        path: Absolute path to the image to OCR.

    Returns:
        OCR text extracted from the image.
    """
    cfg = env_paths()
    img_path = Path(path)
    if not img_path.exists():
        return f"File not found: {path}"
    return vlm_ocr_image(img_path, cfg)


@tool(parse_docstring=True)
def hash_file(path: str, algorithm: Literal["sha256", "md5"] = "sha256") -> str:
    """Compute a file hash for duplicate detection.

    Args:
        path: Absolute path to the file.
        algorithm: Hash algorithm to use.

    Returns:
        Hex digest of the file.
    """
    target = Path(path)
    if not target.exists():
        return f"File not found: {path}"
    return get_file_hash(target, algorithm=algorithm)


@tool(parse_docstring=True)
def apply_file_mapping(
    mapping_json: str,
    source_root: str | None = None,
    destination_root: str | None = None,
    operation: Literal["move", "copy"] = "move",
    allow_overwrite: bool = False,
    dry_run: bool = True,
) -> str:
    """Apply or preview a file mapping for reconstruction.

    Args:
        mapping_json: JSON mapping (dict or list) from source to destination.
        source_root: Root directory for relative source paths (defaults to the
            uploads area under the work root).
        destination_root: Root directory for relative destination paths (defaults
            to the output area under the work root).
        operation: "move" or "copy".
        allow_overwrite: Whether to overwrite existing destination files.
        dry_run: If true, only return the planned actions.

    Returns:
        JSON summary of actions and errors.
    """
    try:
        mapping = json.loads(mapping_json)
    except json.JSONDecodeError as exc:
        return json.dumps({"errors": [f"Invalid JSON: {exc}"]}, indent=2)

    cfg = env_paths()
    source_root = source_root or cfg["upload"]
    destination_root = destination_root or cfg["output"]

    actions, errors = prepare_file_mapping(
        mapping, source_root=source_root, destination_root=destination_root
    )
    payload = {
        "dry_run": dry_run,
        "operation": operation,
        "source_root": source_root,
        "destination_root": destination_root,
        "actions": actions,
        "errors": errors,
    }

    if errors:
        return json.dumps(payload, indent=2)
    if dry_run:
        return json.dumps(payload, indent=2)

    if not allow_overwrite:
        collisions = [
            action["destination"]
            for action in actions
            if Path(action["destination"]).exists()
        ]
        if collisions:
            payload["errors"].extend(
                [f"Destination exists: {path}" for path in collisions]
            )
            return json.dumps(payload, indent=2)

    try:
        results = execute_file_mapping(
            actions, operation=operation, allow_overwrite=allow_overwrite
        )
        payload["results"] = results
    except Exception as exc:
        payload["errors"].append(str(exc))

    return json.dumps(payload, indent=2)


@tool(parse_docstring=True)
def vectorize_text_tool(text: str, source_path: str) -> str:
    """Chunk text and ingest into FAISS.

    Args:
        text: Raw text to chunk and embed.
        source_path: Original file path for metadata.

    Returns:
        Summary including chunk count and FAISS index path.
    """
    cfg = env_paths()
    chunks, index_path = vectorize_text(text, source_path, cfg)
    if chunks == 0:
        return "No text ingested (empty)."
    return f"Ingested {chunks} chunks into {index_path}"
