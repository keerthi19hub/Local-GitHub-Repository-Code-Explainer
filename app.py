"""
app.py
======
Main Streamlit application for the Local GitHub Repository Code Explainer.
Entrypoint for Streamlit Community Cloud:
    streamlit run app.py

Features:
- Multi-Laptop Architecture: Each user communicates with their OWN local Ollama & Qwen 2.5 3B model.
- Browser-Side Ollama Connector: Invokes local Ollama from the user's browser, eliminating central servers.
- Full Repository Inventory: 12 file categories, sensitive file protection, notebook cell extraction.
- Smart Low-Latency Context: Grounded 23-point evidence prompt with zero hallucination.
"""

from __future__ import annotations

import os
import time
import streamlit as st

from backend.llm_service import OllamaService
from backend.models import AnalyzeResponse, RepositoryProcessingError
from backend.repository_analyzer import RepositoryAnalyzer
from components.ollama_connector import render_ollama_connector

# Configure page layout and title
st.set_page_config(
    page_title="GitHub Repository Code Explainer",
    page_icon="🤖",
    layout="wide",
)

# Initialize per-session state
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "current_url" not in st.session_state:
    st.session_state.current_url = ""
if "local_explanation" not in st.session_state:
    st.session_state.local_explanation = None

# App Header
st.title("GITHUB REPOSITORY CODE EXPLAINER")
st.caption("Understand any public GitHub repository using local Ollama + Qwen 2.5 3B.")

# Quick status probe for local environment
ollama_service = OllamaService()
status_probe = ollama_service.check_status()

# Top status header
col_s1, col_s2, col_s3 = st.columns([2, 2, 3])
with col_s1:
    if status_probe.connected:
        st.success("🟢 Local Ollama: CONNECTED", icon="✅")
    else:
        st.warning("⚪ Local Ollama: Standby / Browser Managed", icon="💻")

with col_s2:
    if status_probe.model_available:
        st.success("🟢 Qwen 2.5 3B: AVAILABLE", icon="🤖")
    else:
        st.info("ℹ️ Qwen 2.5 3B: Detected via Browser", icon="🔍")

with col_s3:
    st.caption("Each user uses their OWN laptop's Ollama instance. No shared cloud server or paid API keys required.")

# Sidebar with First-Time Setup Instructions and Multi-Laptop Details
with st.sidebar:
    st.header("Local Ollama Setup")
    st.markdown(
        """
        **Every user uses their own local AI model:**
        1. **Install Ollama** from [ollama.com](https://ollama.com).
        2. **Download Qwen 2.5 3B:**
           ```bash
           ollama pull qwen2.5:3b
           ```
        3. **Start Ollama with Browser Access:**
           - **Windows (PowerShell):**
             ```powershell
             $env:OLLAMA_ORIGINS="*"
             ollama serve
             ```
           - **Mac / Linux:**
             ```bash
             OLLAMA_ORIGINS="*" ollama serve
             ```
        4. Open this app, paste any public repository URL, and analyze!
        """
    )
    st.divider()
    st.subheader("Architecture")
    st.markdown(
        """
        ```
        Streamlit Cloud / Web
                  │
            User Browser
                  │ (Localhost)
            User Laptop
                  │
             Local Ollama
                  │
             Qwen 2.5 3B
        ```
        """
    )
    st.caption("Laptop A uses Ollama A • Laptop B uses Ollama B")

# Input Section
st.subheader("Analyze Any Public GitHub Repository")
col_input, col_btn = st.columns([4, 1])

with col_input:
    repo_url = st.text_input(
        "Enter Public GitHub Repository URL:",
        placeholder="https://github.com/psf/requests",
        help="Paste any public HTTPS repository URL from any GitHub user or organization.",
    )

with col_btn:
    st.write("")  # Alignment spacing
    st.write("")
    analyze_btn = st.button("Analyze Repository", type="primary", use_container_width=True)

# Trigger Analysis
if analyze_btn:
    clean_url = repo_url.strip()
    if not clean_url:
        st.error("Please enter a public GitHub repository URL (e.g., https://github.com/psf/requests).")
        st.stop()

    analyzer = RepositoryAnalyzer()
    status_widget = st.status("Analyzing repository...", expanded=True)
    seen_stages: list[str] = []

    def on_progress(stage: str) -> None:
        if stage not in seen_stages:
            seen_stages.append(stage)
            status_widget.write(f"⏳ {stage}")

    try:
        t_start = time.perf_counter()
        # Analyze repository and build grounded prompt
        result = analyzer.analyze(clean_url, progress=on_progress, generate_ai=False)
        total_time = time.perf_counter() - t_start

        # Store in session state for multi-user safety
        st.session_state.analysis_result = result
        st.session_state.current_url = clean_url
        st.session_state.local_explanation = None

        status_widget.update(label=f"Analysis complete in {total_time:.2f}s!", state="complete", expanded=False)

    except RepositoryProcessingError as exc:
        status_widget.update(label="Analysis halted", state="error", expanded=True)
        st.error(str(exc))
        st.stop()
    except Exception as exc:
        status_widget.update(label="Analysis failed", state="error", expanded=True)
        st.error(f"Unexpected error: {exc}")
        st.stop()

# Display Results if Analysis Exists in Session
res: AnalyzeResponse | None = st.session_state.analysis_result

if res:
    st.divider()

    # 5 Navigation Tabs
    tab_overview, tab_structure, tab_files, tab_ai, tab_tech = st.tabs(
        ["Overview", "Repository Structure", "Files & Folders", "AI Explanation", "Technical Details"]
    )

    # -------------------------------------------------------------
    # TAB 1: OVERVIEW
    # -------------------------------------------------------------
    with tab_overview:
        st.subheader(f"Repository: {res.repository_owner} / {res.repository_name}")
        st.caption(f"Classification: **{res.repository_type}** | URL: `{res.repository_url}`")

        # Inventory metric cards
        counts = res.file_counts
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Total Files", len(res.file_inventory))
        m2.metric("Source Code", counts.get("SOURCE", 0))
        m3.metric("Documentation", counts.get("DOCUMENTATION", 0))
        m4.metric("Dependencies", counts.get("DEPENDENCIES", 0))
        m5.metric("Notebooks", counts.get("NOTEBOOK", 0))
        m6.metric("Sensitive Protected", sum(1 for f in res.file_inventory if f.sensitive))

        st.divider()

        col_l, col_r = st.columns(2)
        with col_l:
            st.markdown("#### Technologies Detected from Evidence")
            if res.technologies:
                st.write(", ".join([f"`{t}`" for t in res.technologies]))
            else:
                st.info("Not clearly established from the available repository files.")

        with col_r:
            st.markdown("#### Programming Languages")
            if res.language_counts:
                for lang, c in res.language_counts.items():
                    st.write(f"• **{lang}:** {c} file{'s' if c > 1 else ''}")
            else:
                st.write("No traditional source programming languages identified.")

    # -------------------------------------------------------------
    # TAB 2: REPOSITORY STRUCTURE
    # -------------------------------------------------------------
    with tab_structure:
        st.subheader("Repository Structure & Directory Layout")
        st.write(f"Sample of top directory hierarchy ({min(len(res.folder_tree), 100)} paths):")
        with st.expander("Expand Folder Tree View", expanded=True):
            st.code("\n".join(res.folder_tree[:100]), language="text")

    # -------------------------------------------------------------
    # TAB 3: FILES & FOLDERS
    # -------------------------------------------------------------
    with tab_files:
        st.subheader("Complete Repository File Inventory")
        st.write(f"Total inspectable items cataloged: **{len(res.file_inventory)}**")

        st.markdown("##### High-Priority Files Selected for Context Analysis:")
        for path in res.selected_files:
            st.write(f"• `{path}`")

        with st.expander("View Full Catalog of All Scanned Files", expanded=False):
            for item in res.file_inventory:
                if item.sensitive:
                    st.write(f"🔒 `{item.path}` — **SENSITIVE FILE** (Contents strictly excluded from context)")
                else:
                    st.write(f"`{item.path}` — *{item.category}* ({item.size_bytes:,} bytes)")

    # -------------------------------------------------------------
    # TAB 4: AI EXPLANATION (OLLAMA + QWEN 2.5 3B)
    # -------------------------------------------------------------
    with tab_ai:
        st.subheader("Detailed AI Explanation (Qwen 2.5 3B)")
        st.caption("Generated through your laptop's local Ollama instance using the grounded evidence context.")

        # Browser-side local Ollama streaming connector
        st.markdown("#### Browser-Side Local Ollama Connector")
        render_ollama_connector(
            prompt=res.llm_prompt,
            default_endpoint="http://127.0.0.1:11434",
            model_name="qwen2.5:3b",
            height=580,
            auto_check=True,
        )

        st.divider()

        # Optional Direct Python Local Fallback (useful for local development)
        with st.expander("Local Development Direct Inference (Python Localhost Fallback)"):
            st.caption("When running locally on your laptop, you can also trigger inference directly via Python.")
            if st.button("Run Direct Python Inference on Localhost", key="btn_direct_infer"):
                with st.spinner("Connecting to local Ollama (qwen2.5:3b)..."):
                    try:
                        explanation, dur = ollama_service.generate_explanation(res.llm_prompt)
                        st.session_state.local_explanation = explanation
                        st.success(f"Generated via local Qwen in {dur:.2f} seconds!")
                    except Exception as err:
                        st.error(f"Direct local inference failed: {err}")

            if st.session_state.local_explanation:
                st.markdown("### Generated Explanation:")
                st.markdown(st.session_state.local_explanation)

    # -------------------------------------------------------------
    # TAB 5: TECHNICAL DETAILS
    # -------------------------------------------------------------
    with tab_tech:
        st.subheader("Technical Performance & Context Metrics")
        st.markdown("##### Stage-by-Stage Latency (Measured via `time.perf_counter`):")

        timings = res.timings
        cols = st.columns(min(len(timings), 4))
        for i, (stage, sec) in enumerate(timings.items()):
            label = stage.replace("_", " ").title()
            cols[i % len(cols)].metric(f"{label}", f"{sec:.2f}s")

        st.divider()
        st.markdown("##### Context Window & Token Budget:")
        c1, c2, c3 = st.columns(3)
        c1.metric("Selected Files for AI", len(res.selected_files))
        c2.metric("Code Context Length", f"{len(res.code_context):,} chars")
        c3.metric("Estimated Input Tokens", f"~{len(res.llm_prompt) // 4:,}")

        with st.expander("Inspect Grounded Qwen Prompt"):
            st.text_area("Prompt Preview", value=res.llm_prompt, height=250, disabled=True)
