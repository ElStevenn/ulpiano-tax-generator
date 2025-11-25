from __future__ import annotations

import shutil
from typing import Optional


def generate_pdf_from_template(
    template_pdf_path: str,
    output_pdf_path: str,
    title: Optional[str] = None,
    subject: Optional[str] = None,
    keywords: Optional[str] = None,
    author: str = "Ulpiano",
) -> None:
    """Copy the official template to the output location and best-effort set metadata.

    If PyPDF2 is available, set document info metadata; otherwise, just copy.
    """
    try:
        import PyPDF2  # type: ignore

        reader = PyPDF2.PdfReader(template_pdf_path)
        writer = PyPDF2.PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        metadata = {}
        if title:
            metadata["/Title"] = title
        if subject:
            metadata["/Subject"] = subject
        if keywords:
            metadata["/Keywords"] = keywords
        if author:
            metadata["/Author"] = author
        if metadata:
            writer.add_metadata(metadata)
        with open(output_pdf_path, "wb") as f:
            writer.write(f)
    except Exception:
        # Fallback to simple copy if PyPDF2 missing or any error occurs.
        shutil.copyfile(template_pdf_path, output_pdf_path)


