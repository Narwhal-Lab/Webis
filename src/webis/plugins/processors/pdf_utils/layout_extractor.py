import pdfplumber
from typing import List, Dict


class PDFLayoutExtractor:


    def extract(self, pdf_path: str) -> List[Dict]:
        blocks: List[Dict] = []

        with pdfplumber.open(pdf_path) as pdf:
            for page_index, page in enumerate(pdf.pages):
                words = page.extract_words(
                    use_text_flow=False,
                    keep_blank_chars=False,
                    extra_attrs=[]
                )

                for w in words:
                    blocks.append({
                        "page": page_index,
                        "text": w["text"],
                        "x0": float(w["x0"]),
                        "x1": float(w["x1"]),
                        "top": float(w["top"]),
                        "bottom": float(w["bottom"]),
                        "width": float(w["x1"] - w["x0"]),
                        "height": float(w["bottom"] - w["top"]),
                    })

        return blocks
