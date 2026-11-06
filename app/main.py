from io import BytesIO
import logging

from PIL import Image, UnidentifiedImageError

from fastapi import FastAPI, HTTPException, UploadFile,File,Form
from fastapi.responses import HTMLResponse
from app.services.document_service import extract_docx_text,analyze_screenshot
from .agents.testcase_agent import generate_test_cases
from .models import GenerateRequest, GenerateResponse
from app.services.website_crawler import crawl_website
import json
from app.services.website_context import prepare_page_context


logger = logging.getLogger(__name__)

app = FastAPI(title="BRD Test-Case Agent", version="0.1.0")


MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_SCREENSHOTS = 5

IMAGE_FORMATS = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}


@app.get("/", response_class=HTMLResponse)
async def upload_page() -> str:
    """UI for uploading BRD documents and multiple screenshots."""
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Test Scenario & Test Case Generator</title>

  <style>
    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: #f4f7fb;
      color: #172033;
      font: 15px/1.6 system-ui, sans-serif;
    }

    main {
      max-width: 980px;
      margin: 40px auto;
      padding: 0 20px 40px;
    }

    .card {
      background: #fff;
      border: 1px solid #dce3ef;
      border-radius: 14px;
      padding: 30px;
      box-shadow: 0 8px 24px #1720330d;
    }

    h1 {
      margin: 0;
      font-size: 28px;
    }

    h2 {
      margin-top: 0;
      font-size: 20px;
    }

    .subtitle {
      color: #64748b;
      margin: 8px 0 28px;
    }

    form {
      display: flex;
      flex-direction: column;
      gap: 22px;
    }

    .form-field {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    label {
      font-weight: 600;
      font-size: 14px;
    }

    .optional {
      color: #94a3b8;
      font-weight: 400;
    }

    input[type="file"],
    input[type="text"],
    textarea {
      width: 100%;
      padding: 12px;
      border: 1px solid #dce3ef;
      border-radius: 9px;
      font: inherit;
      background: #fff;
      color: #172033;
    }

    textarea {
      resize: vertical;
      min-height: 100px;
    }

    input:focus,
    textarea:focus {
      outline: 2px solid #bfdbfe;
      border-color: #2563eb;
    }

    .hint {
      color: #64748b;
      font-size: 12px;
    }

    .file-area {
      background: #f8fafc;
      border: 2px dashed #cbd5e1;
      border-radius: 10px;
      padding: 20px;
    }

    .file-list {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 12px;
    }

    .file-item {
      display: flex;
      align-items: center;
      gap: 8px;
      border: 1px solid #dce3ef;
      border-radius: 8px;
      padding: 8px 10px;
      background: #fff;
      max-width: 100%;
    }

    .file-item span {
      overflow-wrap: anywhere;
      font-size: 13px;
    }

    .remove-btn {
      background: #fee2e2;
      color: #b91c1c;
      border: 0;
      padding: 3px 9px;
      border-radius: 6px;
      cursor: pointer;
    }

    .image-preview {
      width: 70px;
      height: 60px;
      object-fit: cover;
      border-radius: 6px;
      border: 1px solid #e2e8f0;
    }

    .primary-btn {
      background: #2563eb;
      color: #fff;
      font-weight: 600;
      padding: 13px 20px;
      border: 0;
      border-radius: 9px;
      cursor: pointer;
      font-size: 15px;
    }

    .primary-btn:hover {
      background: #1d4ed8;
    }

    .primary-btn:disabled {
      background: #93b4f5;
      cursor: wait;
    }

    .section-divider {
      border: 0;
      border-top: 1px solid #e2e8f0;
      margin: 4px 0;
    }

    #status {
      min-height: 24px;
      margin: 20px 0 0;
      font-weight: 500;
    }

    .success {
      color: #15803d;
    }

    .error {
      color: #dc2626;
    }

    .loading {
      color: #2563eb;
    }

    .results {
      margin-top: 28px;
      border-top: 1px solid #e2e8f0;
      padding-top: 24px;
    }

    .result-block {
      margin-top: 20px;
    }

    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #101827;
      border-radius: 9px;
      color: #e5eefc;
      padding: 22px;
      font: 13px/1.7 ui-monospace, monospace;
      max-height: 650px;
      overflow-y: auto;
    }

    [hidden] {
      display: none !important;
    }

    @media (max-width: 600px) {
      main {
        margin: 15px auto;
        padding: 0 12px;
      }

      .card {
        padding: 18px;
      }

      h1 {
        font-size: 23px;
      }
    }
  </style>
</head>

<body>
  <main>
    <section class="card">

      <h1>AI Test Scenario & Test Case Generator</h1>

      <p class="subtitle">
        Upload a BRD document, UI screenshots, or describe
        your application to generate test scenarios and test cases.
      </p>

      <form id="upload-form">

        <!-- MODULE NAME -->
        <div class="form-field">
          <label for="module">
            Application Module
            <span class="optional">(Optional)</span>
          </label>

          <input
            id="module"
            type="text"
            placeholder="e.g. Login, Registration, Dashboard"
          >
        </div>

        <hr class="section-divider">

        <!-- DOCX UPLOAD -->
        <div class="form-field">

          <label for="file">
            Upload BRD Document
            <span class="optional">(Optional)</span>
          </label>

          <div class="file-area">
            <input
              id="file"
              name="file"
              type="file"
              accept=".docx"
            >

            <div class="hint">
              Supported format: DOCX (Maximum 5 MB)
            </div>
          </div>

          <div id="document-preview" class="file-list"></div>

        </div>

        <!-- MULTIPLE SCREENSHOT UPLOAD -->
        <div class="form-field">

          <label for="screenshots">
            Upload UI Screenshots
            <span class="optional">(Multiple allowed)</span>
          </label>

          <div class="file-area">

            <input
              id="screenshots"
              name="screenshots"
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              multiple
            >

            <div class="hint">
              Upload screenshots of your application's UI.
              Supported: PNG, JPG, JPEG, WebP.
              Maximum 5 screenshots, 5 MB each.
            </div>

          </div>

          <div id="screenshots-preview" class="file-list"></div>

        </div>

        <hr class="section-divider">

        <!-- WEBSITE URL -->
        <div class="form-field">

          <label for="website-url">
            Website URL
            <span class="optional">(Optional)</span>
          </label>

          <input
            id="website-url"
            type="url"
            inputmode="url"
            placeholder="https://example.com"
          >

          <div class="hint">
            Provide a public HTTP or HTTPS website to crawl (up to 2 pages).
          </div>

        </div>

        <hr class="section-divider">

        <!-- DESCRIPTION -->
        <div class="form-field">

          <label for="description">
            Application Description
            <span class="optional">(Optional)</span>
          </label>

          <textarea
            id="description"
            rows="4"
            placeholder="Describe the application, module, features, and expected behavior..."
          ></textarea>

          <div class="hint">
            Provide business rules or functionality that may not be
            visible in screenshots.
          </div>

        </div>

        <!-- ADDITIONAL AI INSTRUCTIONS -->
        <div class="form-field">

          <label for="instructions">
            Additional Instructions to AI
            <span class="optional">(Optional)</span>
          </label>

          <textarea
            id="instructions"
            rows="5"
            placeholder="Enter any specific instructions for scenario generation..."
          ></textarea>

          <div class="hint">
            The AI should use only the inputs provided in this request
            and should not assume unspecified functionality.
          </div>

        </div>

        <!-- SUBMIT -->
        <button
          id="submit"
          class="primary-btn"
          type="submit"
        >
          Generate Scenarios & Test Cases
        </button>

      </form>

      <!-- STATUS -->
      <p id="status" role="status"></p>

      <!-- RESULTS -->
      <div id="results" class="results" hidden>

        <h2>Generated QA Report</h2>

        <div id="scenarios-block" class="result-block" hidden>
          <h2>Test Scenarios</h2>
          <pre id="scenarios-result"></pre>
        </div>

        <div id="testcases-block" class="result-block" hidden>
          <h2>Test Cases</h2>
          <pre id="testcases-result"></pre>
        </div>

        <div id="legacy-block" class="result-block" hidden>
          <pre id="legacy-result"></pre>
        </div>

      </div>

    </section>
  </main>

  <script>

    const form = document.getElementById("upload-form");

    const fileInput = document.getElementById("file");
    const screenshotsInput = document.getElementById("screenshots");

    const moduleInput = document.getElementById("module");
    const websiteUrlInput = document.getElementById("website-url");
    const descriptionInput = document.getElementById("description");
    const instructionsInput = document.getElementById("instructions");

    const button = document.getElementById("submit");
    const status = document.getElementById("status");

    const results = document.getElementById("results");

    const scenariosBlock =
      document.getElementById("scenarios-block");

    const testcasesBlock =
      document.getElementById("testcases-block");

    const legacyBlock =
      document.getElementById("legacy-block");

    const scenariosResult =
      document.getElementById("scenarios-result");

    const testcasesResult =
      document.getElementById("testcases-result");

    const legacyResult =
      document.getElementById("legacy-result");

    const documentPreview =
      document.getElementById("document-preview");

    const screenshotsPreview =
      document.getElementById("screenshots-preview");

    let selectedScreenshots = [];

    const MAX_SCREENSHOTS = 5;
    const MAX_FILE_SIZE = 5 * 1024 * 1024;

    function setStatus(message, type = "") {
      status.textContent = message;
      status.className = type;
    }

    function validImage(file) {
      return [
        "image/png",
        "image/jpeg",
        "image/webp"
      ].includes(file.type);
    }

    // DOCUMENT PREVIEW
    fileInput.addEventListener("change", () => {

      documentPreview.innerHTML = "";

      const file = fileInput.files[0];

      if (!file) return;

      if (!file.name.toLowerCase().endsWith(".docx")) {
        setStatus("Only DOCX documents are supported.", "error");
        fileInput.value = "";
        return;
      }

      if (file.size > MAX_FILE_SIZE) {
        setStatus("Document must be 5 MB or smaller.", "error");
        fileInput.value = "";
        return;
      }

      const item = document.createElement("div");
      item.className = "file-item";

      const filename = document.createElement("span");
      filename.textContent = file.name;

      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "remove-btn";
      remove.textContent = "Remove";

      remove.addEventListener("click", () => {
        fileInput.value = "";
        documentPreview.innerHTML = "";
      });

      item.append(filename, remove);
      documentPreview.appendChild(item);

      setStatus("");
    });


    // SCREENSHOT UPLOAD
    screenshotsInput.addEventListener("change", () => {

      const newFiles = Array.from(screenshotsInput.files);

      for (const file of newFiles) {

        if (!validImage(file)) {
          setStatus(
            `${file.name} is not a supported image.`,
            "error"
          );
          continue;
        }

        if (file.size > MAX_FILE_SIZE) {
          setStatus(
            `${file.name} exceeds 5 MB.`,
            "error"
          );
          continue;
        }

        const exists = selectedScreenshots.some(
          existing =>
            existing.name === file.name &&
            existing.size === file.size &&
            existing.lastModified === file.lastModified
        );

        if (exists) continue;

        if (selectedScreenshots.length >= MAX_SCREENSHOTS) {
          setStatus(
            "Maximum 5 screenshots allowed.",
            "error"
          );
          break;
        }

        selectedScreenshots.push(file);
      }

      screenshotsInput.value = "";

      renderScreenshots();
    });


    function renderScreenshots() {

      screenshotsPreview.innerHTML = "";

      selectedScreenshots.forEach((file, index) => {

        const item = document.createElement("div");
        item.className = "file-item";

        const image = document.createElement("img");
        image.className = "image-preview";
        image.alt = file.name;

        const imageUrl = URL.createObjectURL(file);
        image.src = imageUrl;

        image.onload = () => URL.revokeObjectURL(imageUrl);
        image.onerror = () => URL.revokeObjectURL(imageUrl);

        const filename = document.createElement("span");
        filename.textContent = file.name;

        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "remove-btn";
        remove.textContent = "×";
        remove.setAttribute(
          "aria-label",
          `Remove ${file.name}`
        );

        remove.addEventListener("click", () => {
          selectedScreenshots.splice(index, 1);
          renderScreenshots();
        });

        item.append(image, filename, remove);
        screenshotsPreview.appendChild(item);
      });
    }


    // FORM SUBMISSION
    form.addEventListener("submit", async (event) => {

      event.preventDefault();

      const documentFile = fileInput.files[0];

      const description = descriptionInput.value.trim();
      const instructions = instructionsInput.value.trim();
      const moduleName = moduleInput.value.trim();
      const websiteUrl = websiteUrlInput.value.trim();

      if (
        !documentFile &&
        selectedScreenshots.length === 0 &&
        !description &&
        !websiteUrl
      ) {
        setStatus(
          "Please upload a BRD, screenshots, provide a description, or enter a website URL.",
          "error"
        );
        return;
      }

      button.disabled = true;

      setStatus(
        "Generating scenarios and test cases...",
        "loading"
      );

      results.hidden = true;
      scenariosBlock.hidden = true;
      testcasesBlock.hidden = true;
      legacyBlock.hidden = true;

      scenariosResult.textContent = "";
      testcasesResult.textContent = "";
      legacyResult.textContent = "";

      // Construct multipart request
      const data = new FormData();

      if (documentFile) {
        data.append("file", documentFile);
      }

      for (const screenshot of selectedScreenshots) {
        data.append("screenshots", screenshot);
      }

      data.append("module_name", moduleName);
      data.append("description", description);
      data.append("additional_instructions", instructions);
      data.append("website_url", websiteUrl);

      try {

        const response = await fetch(
          "/api/testcases/generate",
          {
            method: "POST",
            body: data
          }
        );

        const body = await response.json();

        if (!response.ok) {
          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : "Generation failed"
          );
        }

        // New API response format
        const hasScenarios =
          typeof body.scenarios === "string" &&
          body.scenarios.trim().length > 0;

        const hasTestCases =
          typeof body.test_cases === "string" &&
          body.test_cases.trim().length > 0;

        // Support older API returning {"result": "..."}
        const hasLegacyResult =
          typeof body.result === "string" &&
          body.result.trim().length > 0;

        if (!hasScenarios && !hasTestCases && !hasLegacyResult) {
          throw new Error(
            "The AI returned no scenarios or test cases."
          );
        }

        if (hasScenarios) {
          scenariosResult.textContent = body.scenarios;
          scenariosBlock.hidden = false;
        }

        if (hasTestCases) {
          testcasesResult.textContent = body.test_cases;
          testcasesBlock.hidden = false;
        }

        if (!hasScenarios && !hasTestCases && hasLegacyResult) {
          legacyResult.textContent = body.result;
          legacyBlock.hidden = false;
        }

        results.hidden = false;

        setStatus(
          "QA report generated successfully.",
          "success"
        );

      } catch (error) {

        setStatus(
          `Error: ${error.message}`,
          "error"
        );

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
async def generate(
    file: UploadFile | None = File(None),
    screenshots: list[UploadFile] | None = File(None),
    module_name: str = Form(""),
    description: str = Form(""),
    additional_instructions: str = Form(""),
    website_url: str = Form("")
):

    brd_text=""
    ui_details=[]

    # Step 1 keeps crawler evidence in memory only; it is not included in the
    # LLM input until the later evidence-processing step.
    website_pages: list[dict] = []
    website_contexts = []
    website_evidence = ""  
    
    if website_url.strip():
        
        try:
          # The crawler's public-URL checks remain the application-level
          # safeguard. Production also requires network-level egress/SSRF
          # restrictions to prevent access to internal services.
          website_pages = await crawl_website(
              website_url=website_url.strip(),
              max_pages=2,
            )

          

          for page_data in website_pages:

            page_context = prepare_page_context(page_data)

            website_contexts.append(page_context)

          

          if website_contexts:

            website_evidence = json.dumps(
              website_contexts,
              ensure_ascii=False
            )

        except ValueError as error:
            logger.warning("Website crawl rejected an invalid URL")
            raise HTTPException(
                status_code=400,
                detail="Provide a valid public HTTP or HTTPS website URL",
            ) from error
        except Exception as error:
            logger.exception("Website crawl failed")
            raise HTTPException(
                status_code=502,
                detail="Could not crawl the provided website",
            ) from error

        logger.info("Website pages extracted: %d", len(website_pages))
        for page in website_pages:
            logger.info(
                "Website page extracted: content_blocks=%d buttons=%d links=%d forms=%d",
                len(page.get("content_blocks", [])),
                len(page.get("buttons", [])),
                len(page.get("links", [])),
                len(page.get("forms", [])),
            )

    # STEP 1: DOCX extraction (optional)
    if file is not None:
      if not file.filename or not file.filename.lower().endswith(".docx"):
          raise HTTPException(
              status_code=400,
              detail="Only DOCX files are supported"
          )

      content = await file.read(MAX_FILE_SIZE + 1)

      if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
          status_code=413,
          detail="Maximum DOCX file size is 5 MB"
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

    # STEP 2: Validate screenshot count
    uploaded_screenshots = screenshots or []

    if len(uploaded_screenshots) > MAX_SCREENSHOTS:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 screenshots allowed"
        )

    # STEP 3: Process every uploaded screenshot
    for index, screenshot in enumerate(uploaded_screenshots, start=1):

      #Read image bytes
      image_bytes = await screenshot.read(MAX_FILE_SIZE + 1)

      if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
          status_code=413,
          detail=f"Screenshot {index} exceeds 5 MB"
        )
    
      # Verify actual image format
      try:

         with Image.open(BytesIO(image_bytes)) as img:
          image_format = img.format

          if image_format not in IMAGE_FORMATS:
            raise ValueError("Unsupported image format")

          img.verify()

      except (UnidentifiedImageError, OSError, ValueError) as error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid screenshot: {screenshot.filename}"
            ) from error

      mime_type = IMAGE_FORMATS[image_format]

      # STEP 4: Call your vision LLM function
      try:
        analysis = await analyze_screenshot(
          image_bytes,
          mime_type
        )

      except Exception as error:
        print(f"Screenshot analysis error: {error}")

        raise HTTPException(
          status_code=502,
          detail=f"Could not analyze screenshot {index}"
        ) from error

      ui_details.append(
        f"SCREENSHOT {index}: {screenshot.filename}\n"
        f"{analysis}"
      )

    # STEP 5: Combine current inputs
    combined_input = (
        f"MODULE:\n{module_name.strip()}\n\n"
        f"BRD REQUIREMENTS:\n{brd_text}\n\n"
        f"UI SCREENSHOT ANALYSIS:\n{ui_details}\n\n"
        f"{description.strip()}\n\n"
        f"WEBSITE EVIDENCE:\n{website_evidence}\n\n"
      )

    # At least one meaningful input is required.
    if not (
      brd_text.strip()
      or ui_details
      or description.strip()
      or website_url.strip()
      ):
        raise HTTPException(
            status_code=400,
            detail="Provide a DOCX, screenshot, description, or website URL"
          )

    # STEP 6: Invoke your existing agent
    try:
      test_cases = await generate_test_cases(
         combined_input,
         additional_instructions=additional_instructions.strip()
        )

    except Exception as error:
      print(f"Agent error: {error}")

      raise HTTPException(
        status_code=502,
        detail="Failed to generate test cases"
      ) from error

    # STEP 7: Return the response
    return {
      "filename": file.filename if file else None,
      "result": test_cases
      }

