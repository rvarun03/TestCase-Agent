import base64

from langchain_core.messages import HumanMessage, SystemMessage

from..llm import get_vision_llm

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

async def analyze_screenshot(
    image_bytes: bytes,
    mime_type: str
) -> str:

    #1 Encode image bytes
    encoded_image = base64.b64encode(
        image_bytes
    ).decode("utf-8")

    # 2. Construct the image data URL
    image_url = (
        f"data:{mime_type};base64,{encoded_image}"
    )

    # 3. Create a message containing text + image
    messages = [
    SystemMessage(
        content=(
            "You are an expert software testing engineer. "
            "Identify only visible UI elements. "
            "Never invent functionality."
        )
    ),
    HumanMessage(
        content=[
            {
                "type": "text",
                "text": "Analyze this application screenshot."
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        ]
    )
]


    # 4. Call the vision model
    response = await get_vision_llm().ainvoke(messages)

    # 5. Return the analysis
    return response.content
