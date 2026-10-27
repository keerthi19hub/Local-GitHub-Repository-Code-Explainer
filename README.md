# Local GitHub Repository Code Explainer (Prototype)

> **An interactive web application powered by Streamlit and local LLMs (via Ollama) to analyze, explain, and summarize source code repositories offline.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/LLM-Local%20Ollama-black)](https://ollama.ai)

---

## 1. Overview

The **Local GitHub Repository Code Explainer** is an open-source GenAI application that takes any GitHub repository URL (or local folder), parses the project structure, and uses local LLMs (via Ollama) to produce architectural breakdowns, module summaries, and developer explanations without transmitting code to external APIs.

*Note: For the extended production iteration with full test suites and Streamlit Cloud configuration, visit [GITHUB-CODE-EXPLAINER](https://github.com/keerthi19hub/GITHUB-CODE-EXPLAINER).*

---

## 2. Architecture & Components

- `app.py`: Streamlit user interface and application controller.
- `backend/`: Repository cloning, file tree parsing, and code chunking logic.
- `components/`: UI cards, code viewer widgets, and markdown formatters.
- `tests/`: Automated unit tests via pytest (`pytest.ini`).

---

## 3. Quickstart

```bash
# Clone
git clone https://github.com/keerthi19hub/Local-GitHub-Repository-Code-Explainer.git
cd Local-GitHub-Repository-Code-Explainer

# Setup
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run
streamlit run app.py
```

---

## 4. Author

- **Keerthi N** (*Alliance University, BCA*)
