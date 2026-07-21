# HEPARA: High Energy Physics AI Research Assistant

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-google--adk-orange.svg)](https://github.com/google/adk)
[![Model](https://img.shields.io/badge/model-gemini--2.5--flash-purple.svg)](https://deepmind.google/technologies/gemini/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**HEPARA** (High Energy Physics AI Research Assistant) is a specialized research companion designed for physicists working in High Energy Physics. Built on the **Google Agent Development Kit (ADK)** and powered by **Gemini 2.5 Flash**, HEPARA automates literature tracking, citation monitoring, paper analysis, trend analysis, particle-data retrieval, and general research Q&A.

---

## ✨ Features

-   **📊 Citation Monitoring & Analysis:** 
    -   Track your own citation counts and get notified of new citations or publications via `track_citations_updates`.
    -   Fetch detailed citation metrics for any author on INSPIRE-HEP.
    -   Analyze citation graphs: explore what a paper cites (references) or what papers cite it.
-   **📑 arXiv Intelligence:**
    -   Search for papers on arXiv with advanced query support.
    -   **PDF Downloading:** Directly download paper PDFs to your local machine, with best-effort Markdown extraction for easier reading and downstream analysis.
    -   **Stored Paper Listing:** List locally stored arXiv PDFs by ID from your configured download directory.
    -   **Stored Paper Analysis:** Ask HEPARA to analyze, review, or summarize a stored arXiv paper; missing Markdown sidecars are generated from the PDF when possible.
    -   **Local Paper Q&A:** Downloaded papers are indexed into a Chroma database under `PDF_PATH/chroma_db`, so general questions can use local arXiv context before falling back to Google Search.
    -   **Trending Recommendations:** Discover the latest papers based on trending topics in your field (powered by `arxivflow`).
-   **⚛️ PDG Particle Data:**
    -   Retrieve particle masses, decay widths, and lifetimes from the Particle Data Group database.
    -   List decay channels and branching fractions, optionally filtered by requested decay products.
-   **🔌 Optional MCP Tools:** Add local command-based MCP servers through a user-managed `mcp_config.json`; HEPARA creates one MCP subagent per configured server and starts normally when MCP is not configured.
-   **🧩 External Skills:** Add Google ADK skill folders through `SKILL_PATH`; HEPARA can list all available skills and create standalone skill subagents for skills that are not already attached to MCP servers.
-   **🤖 Intelligent Coordination:** A root agent orchestrates its configured specialized sub-agents to provide seamless answers to complex research queries.
-   **🛡️ Robust Reliability:** Enterprise-grade rate limiting and connection pooling for arXiv/INSPIRE-HEP ensures consistent operation without IP blocking.

## 🛠️ Tech Stack

-   **Framework:** [Google Agent Development Kit (ADK)](https://github.com/google/adk-python)
-   **Model:** Google Gemini (configurable, defaults to `gemini-2.5-flash`)
-   **Keyword Extraction:** [arXivFlow](https://github.com/zjzhao1002/arxivflow) with Ollama for local runs or Gemini for Streamlit Community Cloud
-   **PDF Processing:** [PyMuPDF4LLM](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) for Markdown extraction from downloaded PDFs
-   **Local Retrieval:** [ChromaDB](https://www.trychroma.com/) for querying downloaded arXiv papers
-   **Particle Data:** [pdg](https://github.com/particledatagroup/api) Python API for PDG particle properties and branching fractions
-   **External Tools:** [Model Context Protocol](https://modelcontextprotocol.io/) stdio servers configured by the user
-   **Data Sources:** INSPIRE-HEP API, arXiv API, Particle Data Group, Google Search
-   **Environment:** Python 3.13+, [uv](https://github.com/astral-sh/uv)

## 🔗 Related Projects

-   [HEPARA Discord Bot](https://github.com/zjzhao1002/hepara-discord): A Discord bot interface for HEPARA.

---

## 🚀 Quick Start

### Hosted App (Simplest)

Try the deployed Streamlit Community Cloud app: <https://hepara.streamlit.app/>. 
Enter your Gemini API key (`GOOGLE_API_KEY`), INSPIRE-HEP author name (`AUTHOR`), the arXiv categories (`CATEGORIES`), and choose a model in the sidebar, then click **Apply configuration**. 
Then you can chat with the agent. MCP tools and external skills are not enabled in the hosted Streamlit app.

### Docker Local App (Recommended)

The local Streamlit app is available as a Docker image at <https://hub.docker.com/r/zjzhao1002/hepara>. The container includes the Python app and Ollama, so users only need Docker installed.

Pull the image:

```bash
docker pull zjzhao1002/hepara:latest
```

Run the app:

```bash
docker run --rm -p 8501:8501 -p 11434:11434 \
  -v hepara-data:/app/data \
  -v hepara-ollama:/root/.ollama \
  zjzhao1002/hepara:latest
```

Open <http://localhost:8501>, enter your `GOOGLE_API_KEY`, `AUTHOR`, `CATEGORIES`, model settings, and optional MCP/skill paths in the sidebar, then click **Save configuration**. The first startup can take a while because the container starts Ollama and downloads the default `llama3` model if it is not already present in the `hepara-ollama` volume.

The Docker image defaults `MCP_PATH` to `/app/data/mcp_config.json` and `SKILL_PATH` to `/app/data/skill`. The entrypoint creates those persistent locations in the `hepara-data` volume; an empty MCP config simply leaves MCP disabled until you add servers.

The Docker volumes preserve local state across container restarts:

-   `hepara-data` stores the saved `.env`, Streamlit conversation sessions, citation record, downloaded PDFs, generated Markdown sidecars, and Chroma index under `/app/data`.
-   `hepara-ollama` stores downloaded Ollama models under `/root/.ollama`.

To use a different Ollama model:

```bash
docker run --rm -p 8501:8501 -p 11434:11434 \
  -v hepara-data:/app/data \
  -v hepara-ollama:/root/.ollama \
  -e OLLAMA_MODEL=qwen2.5 \
  zjzhao1002/hepara:latest
```

## ⚙️ Installation

### Prerequisites

-   A Google Gemini API Key
-   [Docker](https://www.docker.com/) for the containerized local app
-   Python 3.13 or higher and [uv](https://github.com/astral-sh/uv) for source-based local runs
-   [Ollama](https://ollama.ai/) for source-based local trend recommendations, unless you switch arXivFlow to Gemini

### Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/zjzhao1002/hepara.git
    cd hepara
    ```

2.  **Sync dependencies:**
    ```bash
    uv sync
    ```

3.  **Configure environment variables for local runs:**
    You can create a `.env` file manually in the root directory, or launch the local Streamlit app and save these values from the sidebar:
    ```env
    # Gemini API Key
    GOOGLE_API_KEY=your_api_key_here

    # Gemini Model (Optional, defaults to "gemini-2.5-flash")
    GOOGLE_MODEL="gemini-2.5-flash"

    # User Configuration
    AUTHOR="your name" # To get accurate results, the INSPIRE-HEP author identifier is recommended. 
                       # It should be something like Joe.Smith.1 
    CATEGORIES="hep-ph, hep-th" # The arXiv categories you are interested in
    PDF_PATH="./pdf/" # Local destination for downloaded PDFs, Markdown sidecars, and the Chroma index

    # arXivFlow keyword extraction for local Streamlit
    ARXIVFLOW_KEYWORD_BACKEND="ollama"
    OLLAMA_MODEL="llama3" # Requires Ollama to be installed and running
    ```

4.  **Optionally configure MCP servers and external skills:**
    Copy the example file to the repository root and edit it with any local stdio MCP servers you want HEPARA to use:
    ```bash
    cp mcp_config.example.json mcp_config.json
    ```

    HEPARA creates a dedicated subagent for each valid entry under `mcpServers`. You can use natural server names such as `git`, `memory_server`, or `memory-server`; HEPARA keeps the original server name for listing and tool lookup, and converts it to an ADK-safe internal agent name when needed.

    The supported format is:
    ```json
    {
      "mcpServers": {
        "server_name": {
          "command": "command-to-run",
          "args": ["optional", "arguments"],
          "env": {"OPTIONAL_VARIABLE": "value"}
        }
      }
    }
    ```

    `args` and `env` may be omitted. To keep the file elsewhere, set `MCP_PATH` to an absolute path or a path relative to the process working directory. Missing and empty configuration files simply disable MCP support; malformed files produce a warning without preventing HEPARA from starting.

    Skills are highly recommended for MCP tools because they give each generated subagent task-specific instructions for when and how to use its server. Set `SKILL_PATH` to a directory containing skill folders. For MCP-specific skills, each skill folder name must exactly match the MCP server name in `mcp_config.json`; for example, the `git` MCP server uses `SKILL_PATH/git`, and `memory-server` uses `SKILL_PATH/memory-server`. If no matching skill is found, HEPARA still creates the MCP subagent with a generic MCP-tool instruction.

    Skill folders in `SKILL_PATH` that do not match MCP server names become standalone skill subagents under `skills_agent`. HEPARA also exposes a skill-listing tool that reports all skill folders in `SKILL_PATH`, including MCP-matched skills. Like MCP server names, skill folder names may contain characters such as hyphens; HEPARA keeps the original folder name for listing and converts it to an ADK-safe internal agent name when needed.

    See the [skill examples guide](skill-example/README.md) for the standard ADK skill directory structure and a minimal `energy-converter` example.

    After MCP or skills are configured, you can ask HEPARA which MCP servers or skills are available, then ask which tools a specific MCP server exposes before using that server for a task.

    Restart the application after changing the MCP configuration or skill folders. MCP tools and external skills are available in `streamlit_app_local.py`, the Docker Streamlit app, and CLI/source-agent runs. They remain disabled in `streamlit_app_cloud.py`.

---

## 🏃 Usage

### Local Streamlit Web App

Launch the local chat UI:

```bash
uv run streamlit run streamlit_app_local.py
```

The local Streamlit app provides:

-   A main chat interface for talking with the HEPARA agent.
-   Markdown-rendered assistant responses via Streamlit.
-   A collapsible sidebar configuration section for setting and saving environment variables to `.env`.
-   A collapsible **Conversations** section that shows the last five non-empty conversations by first query and lets you resume one with a click.
-   Slash commands in the chat input for `/help`, `/mcp`, `/skill`, `/paper`, `/update-database`, `/exit`, and `/quit`.
-   Dropdown selectors for `GOOGLE_MODEL` and `OLLAMA_MODEL`, including custom model values.
-   Local PDF downloads saved under `PDF_PATH`, with matching `.md` sidecar files generated when extraction succeeds.
-   Stored paper listing from the PDFs in `PDF_PATH`.
-   Stored paper analysis and summarization from generated Markdown sidecars, with automatic sidecar generation for existing PDFs when possible.
-   General research Q&A through `faq_agent`, which queries `PDF_PATH/chroma_db` first and uses Google Search when local context is unavailable.
-   Particle-property and decay queries through `pdg_agent` for masses, widths, lifetimes, decay channels, and branching fractions.
-   A manual **Check citation updates** button, so citation tracking only runs when requested.

After changing sidebar settings, click **Save configuration** before chatting so the app reloads the agent with the selected environment, model values, `MCP_PATH`, and `SKILL_PATH`. The local app sets `ARXIVFLOW_KEYWORD_BACKEND="ollama"` automatically, so trend recommendations use the configured Ollama model. Missing or empty MCP configuration files and missing skill directories disable those optional features without preventing the app from starting.

Local Streamlit conversations are stored in the same ADK database as the CLI, `.adk/adk_sessions.db`, scoped to the configured `AUTHOR` value or `Guest` when no author is set. Empty sessions are hidden from the **Conversations** section, and each saved conversation is labeled with its first user query rather than its internal session ID.

Slash commands in the local Streamlit chat input mirror the CLI commands. Listing and maintenance commands return their results in the chat without sending the command to the agent. `/exit` and `/quit` end the active conversation in the web UI, so the next regular message starts a new saved conversation.

### Streamlit Community Cloud App

You can use the cloud entry point when deploying your own Streamlit Community Cloud instance:

```bash
streamlit run streamlit_app_cloud.py
```

For Streamlit Community Cloud, configure these values in app secrets or environment variables:

```toml
GOOGLE_API_KEY = "your_api_key_here"
GOOGLE_MODEL = "gemini-2.5-flash"
AUTHOR = "your INSPIRE-HEP author identifier"
CATEGORIES = "hep-ph, hep-th"
```

The cloud app sets `ARXIVFLOW_KEYWORD_BACKEND="gemini"` automatically, does not expose Ollama, MCP, or external skill settings, and uses `GOOGLE_API_KEY` directly for arXivFlow keyword extraction and Google Search fallback. PDFs generated by the `download_pdf` tool are stored in a temporary server directory and shown as in-browser download buttons so users can save them to their own device. When Markdown extraction succeeds, the app also keeps a `.md` sidecar next to the downloaded PDF and a temporary Chroma index for agent-side reading, paper-analysis, and local-context Q&A workflows. PDG particle-property and decay queries are available through the same chat interface.

### Local Docker Image

You can build the image from source by running:

```bash
docker build -t hepara-local .
docker run --rm -p 8501:8501 -p 11434:11434 \
  -v hepara-data:/app/data \
  -v hepara-ollama:/root/.ollama \
  hepara-local
```

See [docker/README.md](docker/README.md#build-and-redeploy) for local image testing, multi-platform Docker Hub publishing, and container redeployment instructions.

### CLI

Launch the terminal assistant:

```bash
uv run main.py
```

The CLI creates a persistent ADK session and prints the resume command when you exit. To continue a previous conversation, run:

```bash
uv run main.py --resume ID
```

Replace `ID` with the session ID printed by the earlier run. CLI session history is stored in `.adk/adk_sessions.db`.

To inspect optional extensions without starting the HEPARA chat session, use the listing flags:

```bash
uv run main.py --mcp
uv run main.py --skill
uv run main.py --paper
```

`--mcp` prints the valid MCP servers from `mcp_config.json` or `MCP_PATH` and exits. `--skill` prints the skill folders from `SKILL_PATH` or the default `skill/` directory and exits. `--paper` prints the stored PDF stems from `PDF_PATH` and exits. These commands do not initialize the HEPARA coordinator, create a chat session, or run the citation update check.

Inside a CLI chat session, use slash commands for local maintenance:

```text
/mcp               List the available MCP servers.
/skill             List the available Skills.
/paper             List the available papers for analysis.
/update-database   Create missing Markdown sidecars for local PDFs and index unindexed files into `PDF_PATH/chroma_db`.
/exit or /quit     End the conversation.
```

The `/paper` command lists stored PDF stems in `PDF_PATH`. The `/update-database` command scans PDFs in `PDF_PATH`, creates missing `.md` sidecars when possible, infers an arXiv ID from the filename or Markdown text when available, and indexes unindexed files into the local Chroma database. Manually named PDFs are indexed with a stable document ID and source filename even when the filename is not an arXiv ID. If an update fails, the CLI prints the error and keeps the chat session running.

Upon startup, HEPARA will:
1.  Initialize your research session.
2.  Automatically check for new citations for the configured `AUTHOR`.
3.  Ready itself for your questions about papers, trends, citations, particle data, or general HEP topics.

### Example Queries

-   *"What are the trending topics in hep-ph this week?"*
-   *"Download the PDF for arXiv:2301.00001"*
-   *"List all stored papers."*
-   *"Summarize stored paper arXiv:2301.00001."*
-   *"Based on my stored papers, what are the main approaches to dark matter freeze-in?"*
-   *"What is the latest status of sterile neutrino searches?"*
-   *"What are the mass and decay width of the top quark?"*
-   *"What is the neutron lifetime?"*
-   *"What are the branching fractions for top-quark decays to a W boson and bottom quark?"*
-   *"Who is citing my latest paper?"*
-   *"Find papers on 'Dark Matter' published in the last month."*
-   *"Which external skills are available?"*
-   *"Which tools does the memory-server MCP server expose?"*

---

## 📁 Project Structure

```bash
├── hepara/
│   ├── agent.py           # Root Coordinator Agent
│   ├── subagents/
│   │   ├── arxiv_agent/       # arXiv search, PDF download/listing, paper analysis, Markdown extraction, and trends
│   │   ├── faq_agent/         # General Q&A over local Chroma context with Google Search fallback
│   │   ├── inspirehep_agent/  # INSPIRE-HEP citation tracking and graph analysis
│   │   ├── mcp_agent/         # Optional per-server subagents for user-configured stdio MCP tools
│   │   ├── skills_agent/      # Optional subagents and listing for external ADK skills
│   │   └── pdg_agent/         # PDG masses, widths, lifetimes, decay channels, and branching fractions
├── mcp_config.example.json  # Example user-managed MCP configuration
├── main.py                # Entry point (CLI)
├── streamlit_app_local.py # Entry point (local Streamlit web app)
├── streamlit_app_cloud.py # Entry point (Streamlit Community Cloud app)
├── utils/                 # MCP, skill, and local paper database helpers
├── Dockerfile             # Containerized local Streamlit + Ollama app
├── docker/                # Container startup scripts
├── pyproject.toml         # Dependencies and project metadata
└── README.md              # This file
```

---

## 🤝 Contributing

Contributions are welcome! Whether it's adding new sub-agents for different data sources or improving the prompts, please feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
