from fastapi import FastAPI, HTTPException, UploadFile,File
from app.services.document_service import extract_docx_text
from .agent import generate_test_cases
from .agents.requirement_agent import analyze_requirements
from app.agents.scenario_agent import design_scenarios
from .models import GenerateRequest, GenerateResponse

app = FastAPI(title="BRD Test-Case Agent", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/testcases/generate")
async def generate(file: UploadFile = File(...)):

    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only DOCX files are supported"
        )

    content = await file.read()

    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 5 MB"
        )

    try:
        brd_text = extract_docx_text(content)
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable DOCX file"
        ) from error

    if not brd_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document contains no extractable text"
        )

    scenarios = await design_scenarios(brd_text)

    return {
        "filename": file.filename,
        "scenarios": scenarios.model_dump()
    }
