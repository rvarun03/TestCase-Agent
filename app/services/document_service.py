from io import BytesIO

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def extract_docx_text(content: bytes) -> str:
    document = Document(BytesIO(content))
    sections = []

    for block in document.iter_inner_content():

        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                sections.append(text)

        elif isinstance(block, Table):
            for row in block.rows:
                values = [
                    cell.text.strip()
                    for cell in row.cells
                ]
                sections.append(" | ".join(values))

    return "\n".join(sections)