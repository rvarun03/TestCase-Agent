from fastapi import FastAPI, HTTPException, UploadFile,File
from fastapi.responses import HTMLResponse
from app.services.document_service import extract_docx_text
from .agents.testcase_agent import generate_test_cases
from .models import GenerateRequest, GenerateResponse

app = FastAPI(title="BRD Test-Case Agent", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
async def upload_page() -> str:
    """A minimal local UI that renders the Markdown-like test-case report."""
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BRD Test-Case Agent</title>
  <style>
    body { margin: 0; background: #f4f7fb; color: #172033; font: 16px/1.5 system-ui, sans-serif; }
    main { max-width: 920px; margin: 48px auto; padding: 0 20px; }
    .card { background: #fff; border: 1px solid #dce3ef; border-radius: 12px; padding: 28px; box-shadow: 0 8px 24px #1720330d; }
    h1 { margin-top: 0; } form { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
    input { max-width: 100%; } button { border: 0; border-radius: 8px; background: #2563eb; color: #fff; cursor: pointer; font-weight: 600; padding: 10px 16px; }
    button:disabled { background: #93b4f5; cursor: wait; } #status { min-height: 24px; margin: 16px 0; }
    #result { white-space: pre-wrap; overflow-wrap: anywhere; background: #101827; border-radius: 8px; color: #e5eefc; padding: 22px; }
  </style>
</head>
<body>
  <main>
    <section class="card">
      <h1>BRD Test-Case Agent</h1>
      <p>Upload a DOCX BRD to generate a concise, readable QA test-case report.</p>
      <form id="upload-form">
        <input id="file" name="file" type="file" accept=".docx" required>
        <button id="submit" type="submit">Generate test cases</button>
      </form>
      <p id="status" role="status"></p>
      <pre id="result" hidden></pre>
    </section>
  </main>
  <script>
    const form = document.getElementById("upload-form");
    const fileInput = document.getElementById("file");
    const button = document.getElementById("submit");
    const status = document.getElementById("status");
    const result = document.getElementById("result");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!fileInput.files.length) return;
      button.disabled = true;
      status.textContent = "Generating test cases…";
      result.hidden = true;
      const data = new FormData();
      data.append("file", fileInput.files[0]);
      try {
        const response = await fetch("/api/testcases/generate", { method: "POST", body: data });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "Generation failed");
        if (!body.result || !body.result.trim()) {
          throw new Error("The model returned no test cases. Please try again.");
        }
        result.textContent = body.result;
        result.hidden = false;
        status.textContent = `Generated test cases for ${body.filename}.`;
      } catch (error) {
        status.textContent = `Error: ${error.message}`;
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/testcases/generate")
async def generate(file: UploadFile = File(...)):

    # Step 1: Validate the uploaded file type
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(
            status_code=400,
            detail="Only DOCX files are supported"
        )

    # Step 2: Read uploaded file
    content = await file.read()

    # Step 3: Validate file size (5 MB maximum)
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum file size is 5 MB"
        )

    # Step 4: Extract BRD text
    try:
        brd_text = extract_docx_text(content)

    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid or unreadable DOCX file"
        ) from error

    # Step 5: Check extracted content
    if not brd_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Document contains no extractable text"
        )

    # Step 6: Invoke the single AI agent
    try:
        test_cases = await generate_test_cases(brd_text)

    except Exception as error:
        print(f"Agent error: {error}")

        raise HTTPException(
            status_code=502,
            detail="Failed to generate test cases"
        ) from error

    # Step 7: Return the response
    return {
        "filename": file.filename,
        "result": test_cases
    }
