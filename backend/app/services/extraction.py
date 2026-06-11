import io
from pathlib import Path

from pypdf import PdfReader


ALLOWED_EXTENSIONS = {".txt", ".log", ".pdf"}


class ExtractionError(ValueError):
    pass


def extract_text(filename: str, content: bytes) -> list[tuple[int | None, str]]:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise ExtractionError("Only .txt, .log, and .pdf files are supported")

    if extension == ".pdf":
        return _extract_pdf(content)

    text = _decode_text(content).strip()
    if not text:
        raise ExtractionError("The uploaded file contains no readable text")
    return [(None, text)]


def _decode_text(content: bytes) -> str:
    if not content:
        return ""

    encodings = ["utf-8-sig"]
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        encodings.insert(0, "utf-16")

    for encoding in encodings:
        try:
            text = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "\x00" not in text:
            return text

    text = content.decode("utf-8", errors="replace")
    if text.count("\x00") > max(1, len(text) // 100):
        raise ExtractionError("The uploaded file appears to be binary, not text")
    return text.replace("\x00", "")


def _extract_pdf(content: bytes) -> list[tuple[int, str]]:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise ExtractionError("Encrypted PDFs are not supported")
        pages = [
            (page_number, (page.extract_text() or "").strip())
            for page_number, page in enumerate(reader.pages, start=1)
        ]
    except ExtractionError:
        raise
    except Exception as exc:
        raise ExtractionError("The PDF could not be read") from exc

    readable_pages = [(number, text) for number, text in pages if text]
    if not readable_pages:
        raise ExtractionError(
            "The PDF has no extractable text; scanned PDFs require OCR"
        )
    return readable_pages
