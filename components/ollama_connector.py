"""
components/ollama_connector.py
==============================
Browser-side local Ollama connector for Streamlit.

Architecture:
When Streamlit is deployed to Streamlit Cloud, Python's localhost is the cloud container.
Therefore, this component runs JavaScript directly inside the USER'S WEB BROWSER.
The browser communicates with the user's own laptop Ollama (http://127.0.0.1:11434).

Laptop A → Laptop A's Browser → Laptop A's Ollama → Qwen 2.5 3B (Laptop A)
Laptop B → Laptop B's Browser → Laptop B's Ollama → Qwen 2.5 3B (Laptop B)
"""

from __future__ import annotations

import json
import streamlit.components.v1 as components


def render_ollama_connector(
    prompt: str = "",
    default_endpoint: str = "http://127.0.0.1:11434",
    model_name: str = "qwen2.5:3b",
    height: int = 560,
    auto_check: bool = True,
) -> None:
    """
    Renders an in-browser Ollama controller and streaming generator.
    Allows the user's browser to query their local Ollama instance and stream
    Qwen 2.5 3B inference in real-time.
    """
    safe_prompt = json.dumps(prompt)
    safe_endpoint = json.dumps(default_endpoint)
    safe_model = json.dumps(model_name)
    safe_auto_check = "true" if auto_check else "false"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        * {{
          box-sizing: border-box;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        body {{
          margin: 0;
          padding: 12px;
          background-color: #0e1117;
          color: #fafafa;
        }}
        .card {{
          background: #1e2530;
          border: 1px solid #2d3748;
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
        }}
        .row {{
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          margin-bottom: 8px;
        }}
        .badge {{
          display: inline-block;
          padding: 4px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
        }}
        .badge-success {{ background: #059669; color: white; }}
        .badge-danger {{ background: #dc2626; color: white; }}
        .badge-warning {{ background: #d97706; color: white; }}
        .badge-neutral {{ background: #4b5563; color: white; }}
        button {{
          background: #2563eb;
          color: white;
          border: none;
          padding: 8px 16px;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: background 0.15s;
        }}
        button:hover {{ background: #1d4ed8; }}
        button:disabled {{ background: #4b5563; cursor: not-allowed; }}
        button.btn-secondary {{
          background: #374151;
        }}
        button.btn-secondary:hover {{
          background: #4b5563;
        }}
        input[type="text"] {{
          background: #0e1117;
          border: 1px solid #374151;
          color: white;
          padding: 6px 10px;
          border-radius: 6px;
          font-size: 13px;
          width: 260px;
        }}
        #output-area {{
          background: #0e1117;
          border: 1px solid #374151;
          border-radius: 6px;
          padding: 14px;
          min-height: 220px;
          max-height: 380px;
          overflow-y: auto;
          white-space: pre-wrap;
          font-size: 13px;
          line-height: 1.5;
          color: #e5e7eb;
        }}
        .stat-pill {{
          font-size: 11px;
          color: #9ca3af;
          background: #111827;
          padding: 3px 8px;
          border-radius: 4px;
        }}
        .error-box {{
          background: #450a0a;
          border: 1px solid #991b1b;
          color: #fecaca;
          padding: 10px;
          border-radius: 6px;
          font-size: 12px;
          margin-top: 8px;
          display: none;
        }}
        .code-snippet {{
          background: #111827;
          padding: 2px 6px;
          border-radius: 4px;
          font-family: monospace;
          color: #38bdf8;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="row" style="justify-content: space-between;">
          <div class="row">
            <strong>Local Laptop Ollama:</strong>
            <span id="badge-ollama" class="badge badge-neutral">Checking...</span>
            <span id="badge-model" class="badge badge-neutral">Model: {model_name}</span>
          </div>
          <div class="row">
            <input type="text" id="endpoint-input" value="http://127.0.0.1:11434" title="Your Laptop Ollama URL" />
            <button id="btn-check" class="btn-secondary" onclick="checkOllama()">Check Local Ollama</button>
          </div>
        </div>

        <div id="error-box" class="error-box"></div>

        <div class="row" style="margin-top: 10px;">
          <button id="btn-generate" onclick="generateWithLocalOllama()" disabled>
            ⚡ Generate Explanation via Local Qwen 2.5 3B
          </button>
          <button id="btn-copy" class="btn-secondary" onclick="copyExplanation()" disabled>
            📋 Copy Explanation
          </button>
          <span id="stat-latency" class="stat-pill" style="display:none;"></span>
          <span id="stat-speed" class="stat-pill" style="display:none;"></span>
        </div>
      </div>

      <div class="card" style="margin-bottom: 0;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 6px;">
          <span style="font-size: 12px; font-weight: 600; color: #9ca3af;">QWEN 2.5 3B STREAMING RESPONSE</span>
          <span id="stream-status" style="font-size: 11px; color: #6b7280;">Idle</span>
        </div>
        <div id="output-area">Prompt ready. Click "Generate Explanation via Local Qwen 2.5 3B" to stream the response directly from your laptop's Ollama instance.</div>
      </div>

      <script>
        const promptText = {safe_prompt};
        const defaultEndpoint = {safe_endpoint};
        const modelName = {safe_model};
        const autoCheck = {safe_auto_check};

        let isGenerating = false;
        let generatedText = "";
        let isOllamaOnline = false;
        let isModelReady = false;

        document.getElementById("endpoint-input").value = defaultEndpoint;

        async function checkOllama() {{
          const endpoint = document.getElementById("endpoint-input").value.trim().replace(/\\/$/, "");
          const badgeOllama = document.getElementById("badge-ollama");
          const badgeModel = document.getElementById("badge-model");
          const errorBox = document.getElementById("error-box");
          const btnGen = document.getElementById("btn-generate");

          badgeOllama.className = "badge badge-neutral";
          badgeOllama.textContent = "Checking...";
          errorBox.style.display = "none";

          try {{
            const res = await fetch(`${{endpoint}}/api/tags`, {{
              method: "GET",
              headers: {{ "Accept": "application/json" }},
            }});

            if (!res.ok) {{
              throw new Error(`Ollama returned status ${{res.status}}`);
            }}

            const data = await res.json();
            const models = (data.models || []).map(m => m.name || "");
            isOllamaOnline = true;
            badgeOllama.className = "badge badge-success";
            badgeOllama.textContent = "CONNECTED";

            const hasModel = models.some(m => m.includes(modelName) || m.startsWith(modelName));
            if (hasModel) {{
              isModelReady = true;
              badgeModel.className = "badge badge-success";
              badgeModel.textContent = `Qwen 2.5 3B Ready`;
              if (promptText && promptText.length > 0) {{
                btnGen.disabled = false;
              }}
            }} else {{
              isModelReady = false;
              badgeModel.className = "badge badge-warning";
              badgeModel.textContent = `Model Missing`;
              showError(`Ollama is running, but <strong>${{modelName}}</strong> was not found. Please open a terminal on your laptop and run: <br/><span class="code-snippet">ollama pull ${{modelName}}</span>`);
            }}
          }} catch (err) {{
            isOllamaOnline = false;
            isModelReady = false;
            btnGen.disabled = true;
            badgeOllama.className = "badge badge-danger";
            badgeOllama.textContent = "NOT CONNECTED";
            badgeModel.className = "badge badge-neutral";
            badgeModel.textContent = `Model: ${{modelName}}`;

            showError(
              `<strong>Browser cannot connect to local Ollama at ${{endpoint}}:</strong><br/>` +
              `1. Ensure Ollama is installed and running (<span class="code-snippet">ollama serve</span>).<br/>` +
              `2. Allow browser origin access by setting the environment variable on your laptop:<br/>` +
              `&nbsp;&nbsp;&nbsp;<strong>Windows:</strong> <span class="code-snippet">$env:OLLAMA_ORIGINS="*"</span> then restart Ollama.<br/>` +
              `&nbsp;&nbsp;&nbsp;<strong>Mac/Linux:</strong> <span class="code-snippet">OLLAMA_ORIGINS="*" ollama serve</span><br/>` +
              `3. If on HTTPS Streamlit Cloud, allow insecure localhost connections in your browser site settings.`
            );
          }}
        }}

        function showError(msg) {{
          const errorBox = document.getElementById("error-box");
          errorBox.innerHTML = msg;
          errorBox.style.display = "block";
        }}

        async function generateWithLocalOllama() {{
          if (isGenerating) return;
          if (!promptText || promptText.length === 0) {{
            alert("No repository analysis prompt available. Please click 'Analyze Repository' in Streamlit first.");
            return;
          }}

          const endpoint = document.getElementById("endpoint-input").value.trim().replace(/\\/$/, "");
          const outputArea = document.getElementById("output-area");
          const streamStatus = document.getElementById("stream-status");
          const btnGen = document.getElementById("btn-generate");
          const btnCopy = document.getElementById("btn-copy");
          const statLatency = document.getElementById("stat-latency");
          const statSpeed = document.getElementById("stat-speed");

          isGenerating = true;
          btnGen.disabled = true;
          outputArea.textContent = "";
          generatedText = "";
          streamStatus.textContent = "Streaming from local Qwen 2.5 3B...";
          statLatency.style.display = "none";
          statSpeed.style.display = "none";

          const startTime = performance.now();
          let tokenCount = 0;

          try {{
            const response = await fetch(`${{endpoint}}/api/generate`, {{
              method: "POST",
              headers: {{
                "Content-Type": "application/json",
              }},
              body: JSON.stringify({{
                model: modelName,
                prompt: promptText,
                stream: true,
                keep_alive: "10m",
                options: {{
                  num_predict: 850,
                  temperature: 0.2,
                  repeat_penalty: 1.15
                }}
              }}),
            }});

            if (!response.ok) {{
              throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
            }}

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";

            while (true) {{
              const {{ value, done }} = await reader.read();
              if (done) break;

              buffer += decoder.decode(value, {{ stream: true }});
              const lines = buffer.split("\\n");
              buffer = lines.pop(); // keep partial line

              for (const line of lines) {{
                const trimmed = line.trim();
                if (!trimmed) continue;
                try {{
                  const chunk = JSON.parse(trimmed);
                  if (chunk.response) {{
                    generatedText += chunk.response;
                    tokenCount++;
                    outputArea.textContent = generatedText;
                    outputArea.scrollTop = outputArea.scrollHeight;
                  }}
                  if (chunk.done) {{
                    break;
                  }}
                }} catch (e) {{
                  // partial chunk ignore
                }}
              }}
            }}

            const elapsedSec = ((performance.now() - startTime) / 1000).toFixed(2);
            const tokensPerSec = (tokenCount / Math.max(elapsedSec, 0.1)).toFixed(1);

            streamStatus.textContent = `Completed in ${{elapsedSec}}s`;
            statLatency.textContent = `Generation time: ${{elapsedSec}}s`;
            statLatency.style.display = "inline-block";
            statSpeed.textContent = `Tokens: ~${{tokenCount}} (~${{tokensPerSec}} t/s)`;
            statSpeed.style.display = "inline-block";
            btnCopy.disabled = false;

          }} catch (err) {{
            outputArea.textContent = `Error during generation: ${{err.message}}\\n\\nPlease ensure your local Ollama is active and allows requests from this web page.`;
            streamStatus.textContent = "Failed";
          }} finally {{
            isGenerating = false;
            btnGen.disabled = false;
          }}
        }}

        function copyExplanation() {{
          if (!generatedText) return;
          navigator.clipboard.writeText(generatedText).then(() => {{
            const btnCopy = document.getElementById("btn-copy");
            const original = btnCopy.textContent;
            btnCopy.textContent = "✅ Copied!";
            setTimeout(() => {{ btnCopy.textContent = original; }}, 2000);
          }});
        }}

        // Initial check on load
        if (autoCheck) {{
          checkOllama();
        }}
      </script>
    </body>
    </html>
    """

    components.html(html_code, height=height, scrolling=True)
