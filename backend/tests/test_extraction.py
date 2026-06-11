import io

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    DecodedStreamObject,
    DictionaryObject,
    NameObject,
)

from app.services.extraction import ExtractionError, extract_text


def test_extracts_utf8_text() -> None:
    pages = extract_text("alerts.log", b"failed login from 192.0.2.10")
    assert pages == [(None, "failed login from 192.0.2.10")]


def test_extracts_utf16_text() -> None:
    content = "alert user=jsmith".encode("utf-16")
    assert extract_text("alerts.txt", content) == [(None, "alert user=jsmith")]


def test_extracts_pdf_text() -> None:
    pages = extract_text("incident.pdf", _pdf_with_text("PDF alert from 203.0.113.7"))
    assert pages == [(1, "PDF alert from 203.0.113.7")]


def test_rejects_unsupported_extension() -> None:
    with pytest.raises(ExtractionError):
        extract_text("alerts.csv", b"event,data")


def test_rejects_empty_text() -> None:
    with pytest.raises(ExtractionError):
        extract_text("empty.txt", b"   ")


def test_rejects_binary_text_file() -> None:
    with pytest.raises(ExtractionError):
        extract_text("payload.log", b"\x00\x01\x00\x02")


def _pdf_with_text(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)

    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    resources = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    page[NameObject("/Resources")] = resources

    stream = DecodedStreamObject()
    escaped_text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET".encode())
    page[NameObject("/Contents")] = writer._add_object(stream)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
