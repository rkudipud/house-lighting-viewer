"""Render the editable wardrobe review SVG as a vector PDF and preview PNG."""

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "handoff" / "contractor" / "wardrobe" / "current" / "wardrobe-and-granite-plinth"


def main():
    with pymupdf.open(stream=BASE.with_suffix(".svg").read_bytes(), filetype="svg") as source:
        pdf = source.convert_to_pdf()
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        if document.page_count != 1:
            raise ValueError("The wardrobe review must be one page")
        document.set_metadata({
            "title": "Wardrobe and granite plinth - homeowner review",
            "subject": "Diagrammatic material and layout review; not for fabrication",
        })
        document[0].get_pixmap(matrix=pymupdf.Matrix(2, 2), alpha=False).save(
            BASE.with_suffix(".png")
        )
        document.save(BASE.with_suffix(".pdf"), garbage=4, deflate=True, no_new_id=True)
    print("Rendered wardrobe review PDF and PNG from the editable SVG")


if __name__ == "__main__":
    main()
