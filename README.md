# 💻 Local Code Explainer — Offline Semantic Repository Interpreter & Static Analyzer

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1E293B,0F766E,14B8A6&height=220&section=header&text=Local%20Code%20Explainer&fontSize=42&fontColor=ffffff&fontAlignY=38&desc=Offline%20Semantic%20Repository%20Interpreter%20%26%20Static%20Analyzer&descSize=18&descAlignY=60&descAlign=50" width="100%" alt="Local Code Explainer Banner" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Language-Python%203.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Frontend-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit" />
  <img src="https://img.shields.io/badge/Inference-Local%20Ollama-1E293B?style=for-the-badge" alt="Ollama" />
  <img src="https://img.shields.io/badge/Testing-Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Deployment-Streamlit%20Cloud-14B8A6?style=for-the-badge" alt="Streamlit Cloud" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
</p>

---

## 📌 Table of Contents

- [📖 Executive Summary](#-executive-summary)
- [🎯 Problem Statement & Offline Solution](#-problem-statement--offline-solution)
- [✨ Key Features & Capabilities](#-key-features--capabilities)
- [🏗️ Component Architecture & Workflow](#️-component-architecture--workflow)
- [🛠️ Tech Stack Matrix](#️-tech-stack-matrix)
- [⚙️ Reproducible Quickstart & Setup](#️-reproducible-quickstart--setup)
- [📁 Project Structure](#-project-structure)
- [🧪 Automated Unit Testing](#-automated-unit-testing)
- [👩‍💻 Author & Contributions](#-author--contributions)

---

## 📖 Executive Summary

The **Local Code Explainer** is a standalone, offline developer tool designed to interpret, summarize, and navigate complex software repositories without requiring external internet connectivity or proprietary API keys. Integrating **Streamlit**, a modular Python backend, and a local **Ollama** LLM runtime, the platform enables software developers, code reviewers, and security researchers to inspect internal corporate or proprietary repositories while maintaining total air-gapped security.

---

## 🎯 Problem Statement & Offline Solution

- **The Problem:** Enterprise development environments operating in defense, banking, or medical sectors prohibit the egress of proprietary source code to external cloud endpoints (such as OpenAI or Anthropic). Engineers in these environments lack modern AI code summarization tools.
- **The Solution:** A fully self-contained offline architecture. Developers point the tool at any local repository path; the system builds an interactive directory tree, extracts function signatures, and streams clear natural-language technical explanations directly inside a local Streamlit session.

---

## ✨ Key Features & Capabilities

- **🔒 Zero Data Egress:** 100% offline inference ensuring compliance with strict data protection and corporate confidentiality policies.
- **🌲 Dynamic Tree Browser:** Real-time collapsible file tree with automatic exclusion of `.git`, `node_modules`, and virtual environments.
- **⚡ Syntax-Aware Code Cards:** Formats code snippets with language-specific syntax highlighting alongside LLM explanations.
- **🧪 Pytest Quality Harness:** Includes unit test suites (`pytest.ini`, `tests/`) validating path handling, tree parsing, and error boundaries.

---

## 🏗️ Component Architecture & Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Local Code Explainer Architecture                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Input: Local Path Selector (Air-Gapped Workstation)                         │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Backend Engine (`backend/`):                                                │
│ - Path validation and safe directory traversal                              │
│ - Multi-language source file reader (.py, .js, .ts, .java, .c)              │
│ - Token window splitter & prompt builder                                    │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Local Inference Bridge: Ollama Daemon (`localhost:11434`)                   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Presentation (`app.py` & `components/`):                                    │
│ ┌─────────────────────────┐ ┌─────────────────────────┐ ┌────────────────┐  │
│ │ File Explorer Tree      │ │ Reactive Explanation UI │ │ Status Telemetry │  │
│ └─────────────────────────┘ └─────────────────────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack Matrix

| Domain | Technology | Implementation Details |
| :--- | :--- | :--- |
| **User Interface** | Streamlit | Clean reactive UI layout, sidebar directory browser |
| **Language** | Python 3.10+ | Core application runtime and static parsing |
| **Inference Engine** | Local Ollama | Llama 3 / CodeLlama local model serving |
| **Testing** | Pytest (`pytest.ini`) | Automated unit test harness |

---

## ⚙️ Reproducible Quickstart & Setup

### Prerequisites
1. Python 3.10 or newer.
2. [Ollama installed](https://ollama.ai) with a local model pulled:
   ```bash
   ollama pull llama3
   ```

### 1. Clone the Repository
```bash
git clone https://github.com/keerthi19hub/Local-GitHub-Repository-Code-Explainer.git
cd Local-GitHub-Repository-Code-Explainer
```

### 2. Setup Virtual Environment & Dependencies
```bash
python -m venv venv
venv\Scripts\activate  # Linux/macOS: source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Launch the Application
```bash
streamlit run app.py
```
Open `http://localhost:8501` to start analyzing any local repository path.

---

## 📁 Project Structure

```text
Local-GitHub-Repository-Code-Explainer/
├── app.py              # Streamlit application dashboard
├── backend/            # Repository crawler, file reading, and prompt construction
├── components/         # Reusable UI widgets (tree viewer, code display card)
├── tests/              # Automated unit tests
├── requirements.txt    # Application dependencies
├── pytest.ini          # Pytest configuration directives
├── runtime.txt         # Python runtime environment declaration
└── README.md           # Production technical documentation
```

---

## 🧪 Automated Unit Testing

Run the automated test suite to verify file reading and parser stability:
```bash
pytest tests/ -v
```

---

## 👩‍💻 Author & Contributions

**Keerthi N**  
- **GitHub:** [@keerthi19hub](https://github.com/keerthi19hub)  
- **Portfolio:** [keerthi19hub.github.io](https://keerthi19hub.github.io)  
- **Role:** End-to-end design, modular backend implementation, Streamlit UI components, and unit testing.

---

<p align="center">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=1E293B,0F766E,14B8A6&height=100&section=footer" width="100%" alt="Footer Banner" />
</p>
