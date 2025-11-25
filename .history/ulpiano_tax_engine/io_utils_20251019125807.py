from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Tuple


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_text_file(path: str, content: str, encoding: str = "utf-8") -> None:
    directory = os.path.dirname(path)
    if directory:
        ensure_dir(directory)
    with open(path, "w", encoding=encoding) as f:
        f.write(content)


def compute_output_paths(
    model_code: str,
    generation_id: str,
    now: datetime,
    output_dir: str,
) -> Tuple[str, str]:
    # Timestamp format: YYYY-MM-DDTHH-MM-SSZ (no colons)
    ts = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    base_name = f"M{model_code}_{generation_id}_{ts}"
    output_dir_abs = os.path.abspath(output_dir)
    pdf_path = os.path.join(output_dir_abs, f"{base_name}.pdf")
    xml_path = os.path.join(output_dir_abs, f"{base_name}.xml")
    return pdf_path, xml_path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


