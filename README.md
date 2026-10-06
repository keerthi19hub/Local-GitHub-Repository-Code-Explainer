# Local GitHub Repository Code Explainer

An open-source GenAI application that accepts **ANY** public GitHub repository URL and generates a comprehensive, beginner-friendly, evidence-based explanation of the codebase using **Ollama + Qwen 2.5 3B**.

---

## 1. Project Objective & Mini Assessment Overview

When reviewing unfamiliar open-source projects on GitHub, developers, educators, and students often struggle to understand complex directory layouts, undocumented logic, and unfamiliar dependencies.

The **Local GitHub Repository Code Explainer** automates this by:
1. Cloning any public repository safely using a shallow git clone (`depth=1`).
2. Cataloging the complete repository inventory across 12 file categories.
3. Protecting sensitive credentials (`.env`, secrets, private keys).
4. Safely extracting Jupyter notebook cells without executing code.
5. Detecting technologies and frameworks strictly from verified evidence.
6. Assembling a bounded, low-latency smart context window.
7. Generating a detailed 23-point explanation using a **locally running Qwen 2.5 3B model via Ollama** on the user's laptop.

---

## 2. Multi-Laptop Architecture (Critical Design)

Traditional cloud GenAI applications either rely on expensive paid APIs (OpenAI, Gemini) or require a central personal laptop running an Ollama daemon exposed through brittle tunnels (ngrok, cloudflared). If the host laptop closes, everyone loses access.

This application implements a **decentralized, browser-mediated multi-laptop architecture**:

```
                    STREAMLIT CLOUD
             (Runs app.py & Repo Processor)
                           │
                           │ Transmits Grounded Prompt
                           ▼
                    USER'S WEB BROWSER
             (Custom In-Browser Ollama Client)
                           │
                           │ Calls http://127.0.0.1:11434 (Localhost)
                           ▼
                  USER'S LOCAL OLLAMA
                  (Running on User's Laptop)
                           │
                           ▼
                      QWEN 2.5 3B
              (Streams Tokens Live to Browser)
```

### How Multi-Laptop Operation Works:
- **User A** opens the Streamlit application on **Laptop A** → Browser communicates with **Ollama A** → Runs **Qwen 2.5 3B on Laptop A**.
- **User B** opens the same application on **Laptop B** → Browser communicates with **Ollama B** → Runs **Qwen 2.5 3B on Laptop B**.
- **User C** opens the same application on **Laptop C** → Browser communicates with **Ollama C** → Runs **Qwen 2.5 3B on Laptop C**.

> **No central Ollama server is needed.** No ngrok. No cloudflared. Every user leverages their own local compute!

---

## 3. Technology Stack

| Layer | Technology | Role |
|---|---|---|
| **Frontend** | Streamlit | Responsive multi-tab dashboard with live status cards |
| **Browser Connector** | Streamlit Component (HTML5/JS) | In-browser client fetching `http://127.0.0.1:11434` with SSE token streaming |
| **Backend Service** | Python 3.12 / FastAPI / Uvicorn | Modular service layer and optional REST API |
| **Data Validation** | Pydantic v2 | Request/response schemas and URL validation |
| **Git Engine** | GitPython | Safe shallow repository cloning (`depth=1`) |
| **Local LLM Engine** | Ollama | Local model runner and API daemon |
| **Language Model** | `qwen2.5:3b` | 3.1-Billion parameter lightweight instruction-tuned LLM |
| **Testing** | pytest | Automated test suite validating all 30 core requirements |

---

## 4. End-to-End Processing Pipeline

```
GitHub Repository URL
        ↓
URL Validation & Normalization (github.com only, owner/repo)
        ↓
GitPython Shallow Clone (depth=1, single_branch=True)
        ↓
Full Inventory Scan (12 distinct categories, full directory traversal)
        ↓
Security Shielding (sensitive files identified, contents hidden from context)
        ↓
Notebook Parsing (.ipynb JSON extraction without execution)
        ↓
Technology Detection (strictly from manifests & imports; no hallucination)
        ↓
Smart Context Builder (priority scoring, max 35k chars, max 25 files)
        ↓
Grounded 23-Section Qwen Prompt
        ↓
Browser Connector / FastAPI / Local Ollama (http://127.0.0.1:11434)
        ↓
Qwen 2.5 3B Inference (keep_alive: 10m, token streaming)
        ↓
Detailed Explanation Rendered on Streamlit Frontend
```

---

## 5. Local Setup Guide

### Step 1: Install Ollama & Pull Qwen 2.5 3B
1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Open your terminal or PowerShell and pull the model:
   ```bash
   ollama pull qwen2.5:3b
   ```

### Step 2: Enable Browser Cross-Origin Access (OLLAMA_ORIGINS)
Because modern browsers enforce cross-origin security between web applications and localhost, configure Ollama to accept browser requests:

- **Windows (PowerShell):**
  ```powershell
  $env:OLLAMA_ORIGINS="*"
  ollama serve
  ```
- **Windows (System Environment Variables):**
  Add System Variable `OLLAMA_ORIGINS` with value `*` and restart Ollama from the system tray.
- **macOS / Linux:**
  ```bash
  OLLAMA_ORIGINS="*" ollama serve
  ```

### Step 3: Set Up the Python Project
```bash
# Clone the repository
git clone https://github.com/keerthi19hub/Local-GitHub-Repository-Code-Explainer.git
cd Local-GitHub-Repository-Code-Explainer

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 4: Run the Streamlit Application
```bash
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

---

## 6. Optional: Run FastAPI Backend

To run the REST API independently:
```bash
uvicorn backend.main:app --reload --port 8000
```
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`
- Ollama Status: `http://localhost:8000/api/ollama-status`
- Analyze Repository: `POST http://localhost:8000/api/analyze`

---

## 7. Streamlit Community Cloud Deployment

1. Push your repository to GitHub:
   - Repository: `keerthi19hub/Local-GitHub-Repository-Code-Explainer`
   - Branch: `main`
2. Open [share.streamlit.io](https://share.streamlit.io).
3. Click **"New app"**.
4. Configure:
   - **Repository:** `keerthi19hub/Local-GitHub-Repository-Code-Explainer`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Click **"Deploy!"**.
6. **No secrets or cloud API keys required.**

---

## 8. Latency Optimization Strategy

The system is optimized for low latency:
1. **Shallow Clone (`depth=1`):** Clones only the latest revision, eliminating historical commit downloads.
2. **Bounded Context Budget:** Prompt context is capped at **35,000 characters** (~7,000 tokens) with intelligent excerpting of large files (`[TRUNCATED FOR CONTEXT]`).
3. **Single AI Request:** A single grounded prompt generates the entire 23-section explanation, avoiding multiple round-trips.
4. **Ollama Keep-Alive (`keep_alive: "10m"`):** Keeps the model weights loaded in memory, eliminating repeated cold-start loading overhead.
5. **Streaming Tokens:** Streams tokens live directly to the browser DOM so the user sees results immediately.

---

## 9. Security & Safety

- **Zero Code Execution:** The repository analyzer strictly reads files as text. No scripts, installers (`pip`, `npm`, `cargo`), or notebook kernels are ever executed.
- **Sensitive File Shielding:** Any file matching credential patterns (`.env`, `credentials.json`, `secrets.yaml`, `id_rsa`, `*.pem`) is automatically flagged as `SENSITIVE`. Its contents are completely excluded from the AI prompt and never shown in the UI.
- **Localhost Privacy:** Repository code is sent strictly to the user's personal laptop localhost (`http://127.0.0.1:11434`). No code is sent to third-party cloud AI vendors.

---

## 10. Automated Testing

Run the 30-test automated verification suite:
```bash
pytest -v tests/test_project.py
```
*(Verified: All 30 tests pass in ~1.15 seconds)*

To compile all Python files:
```bash
python -m compileall .
```

---

## 11. Viva & Teacher Demonstration Q&A

1. **"What is the objective of this project?"**
   > *"Mam, our project is a Generative AI application that takes any public GitHub repository URL and automatically explains the codebase in simple language using an evidence-based local model."*

2. **"Which model and platform are you using?"**
   > *"We are strictly using Ollama with the Qwen 2.5 3B parameter model running locally on the user's machine."*

3. **"If the app is deployed on the cloud, how can other students use it on their laptops?"**
   > *"Mam, we built a browser-side Ollama connector in `components/ollama_connector.py`. The cloud server analyzes the repository and builds the prompt, but the user's browser makes the call to `http://127.0.0.1:11434` on their own laptop. This ensures every student uses their own laptop's Ollama without needing central servers or ngrok."*

4. **"How do you prevent hallucinations?"**
   > *"Our prompt builder in `backend/context_builder.py` provides exact file inventories, language counts, and extracted source code snippets with strict instructions that forbid inventing files, frameworks, or databases."*

5. **"How do you handle security?"**
   > *"We never execute repository code, we parse notebooks as raw JSON, and we automatically detect and shield sensitive files like `.env` and secrets from the AI prompt."*
