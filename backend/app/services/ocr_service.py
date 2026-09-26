"""PDF text extraction with PyMuPDF and Tesseract for low-text pages.

Original files are never modified. OCR text is stored separately.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.core.logging import log

MIN_TEXT_CHARS = 30


@dataclass
class PageText:
    page_number: int
    text: str
    is_scanned: bool
    ocr_confidence: float | None
    processing_time: float | None
    ocr_status: str | None
    char_count: int


def _configure_tesseract() -> None:
    settings = get_settings()
    if not settings.tesseract_path:
        return
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_path
    except ImportError:
        log.warning("pytesseract is not installed")


def tesseract_available() -> bool:
    _configure_tesseract()
    try:
        import pytesseract

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _ocr_image(image) -> tuple[str, float | None]:
    import pytesseract

    settings = get_settings()
    data = pytesseract.image_to_data(image, lang=settings.ocr_language, output_type=pytesseract.Output.DICT)
    words = []
    confs = []
    for word, conf in zip(data.get("text", []), data.get("conf", [])):
        if not word or not str(word).strip():
            continue
        words.append(word)
        try:
            value = float(conf)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            confs.append(value)
    text = " ".join(words).strip()
    confidence = (sum(confs) / len(confs) / 100.0) if confs else None
    return text, confidence


def extract_pdf(path: Path) -> list[PageText]:
    import fitz
    from PIL import Image

    _configure_tesseract()
    doc = fitz.open(path)
    pages: list[PageText] = []
    can_ocr = tesseract_available()
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        stripped = text.strip()
        if len(stripped) >= MIN_TEXT_CHARS:
            pages.append(
                PageText(index, stripped, False, None, None, None, len(stripped))
            )
            continue
        started = time.perf_counter()
        if not can_ocr:
            pages.append(
                PageText(
                    index,
                    stripped,
                    True,
                    None,
                    None,
                    "FAILED",
                    len(stripped),
                )
            )
            continue
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        try:
            ocr_text, confidence = _ocr_image(image)
            elapsed = time.perf_counter() - started
            pages.append(
                PageText(
                    index,
                    ocr_text or stripped,
                    True,
                    confidence,
                    elapsed,
                    "COMPLETED" if ocr_text else "FAILED",
                    len(ocr_text or ""),
                )
            )
        except Exception as exc:
            log.exception("OCR failed on page %s: %s", index, exc)
            pages.append(PageText(index, stripped, True, None, time.perf_counter() - started, "FAILED", len(stripped)))
    doc.close()
    return pages


def extract_text_file(path: Path) -> list[PageText]:
    text = path.read_text(encoding="utf-8")
    return [PageText(1, text, False, None, None, None, len(text))]


def extract_csv_file(path: Path) -> list[PageText]:
    import pandas as pd

    frame = pd.read_csv(path)
    text = frame.to_csv(index=False)
    return [PageText(1, text, False, None, None, None, len(text))]
