# Autonomous AI-Powered C# Pull Request Review System

An automated, self-correcting Pull Request code reviewer built in Python 3.13. It analyzes C# code changes via the Gemini REST API and GitHub REST API, automatically mapping inline code feedback and posting high-level architectural summaries back to Pull Requests.

---

## 1. Architecture Overview

This project is built using **Clean Architecture** principles, segregating data structures, integrations, and core business processes:

```
src/
├── main.py                    # Application Entrypoint & Bootstrapper
├── agent/                     # Autonomous Review Agent Lifecycle Orchestrator
│   ├── review_agent.py        # Orchestrates the 6-stage lifecycle
│   ├── agent_state_machine.py # Manages states: OBSERVING, ANALYZING, etc.
│   └── execution_context.py   # Runtime metrics and execution telemetry
├── core/                      # Core System Utilities
│   ├── config.py              # AppConfig settings using Pydantic Settings
│   ├── logging.py             # Structured JSON logger (with auto-masking)
│   ├── exceptions.py          # Custom domain exceptions
│   └── container.py           # Dependency Injection Container
├── integrations/              # External Client Facades
│   ├── github/                # GitHub API reader, fetcher, and publisher
│   └── gemini/                # Direct REST Client with retry exponential backoffs
├── interfaces/                # Abstract Boundary Definitions
├── models/                    # Validated Pydantic Domain schemas
└── services/                  # Business Logic Engines
    ├── diff/                  # Diff extraction, parsing, and line mapping
    ├── prompts/               # Prompt template builders and prompt managers
    ├── review/                # Schema validator, duplicate and severity engines
    └── publishing/            # Summary generation and markdown comment formatters
```

### The 6-Stage Control Loop
1.  **OBSERVE**: Fetches Pull Request metadata, fetches raw diffs, and filters out files matching exclusions.
2.  **ANALYZE**: Compiles modified code into reviewable chunks and requests structured reviews from Gemini.
3.  **VALIDATE**: Parses the output JSON, verifies schema structures, and matches line targets against diff hunks to filter out hallucinations.
4.  **PRIORITIZE**: Removes duplicate findings, filters out low-confidence items, and assigns severity ranks.
5.  **ACT**: Generates the markdown summary report and posts comments (avoiding duplicates from previous commits) using the GitHub API.
6.  **REPORT**: Captures telemetry stats (duration, tokens, chunks processed) and completes the cycle.

---

## 2. Prerequisites & Setup

### Local Workstation Setup
1.  **Python 3.13+**: Ensure Python 3.13 is installed.
2.  **Create Virtual Environment**:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\Activate.ps1
    # macOS/Linux
    source .venv/bin/activate
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration (.env)
Copy `.env.example` to `.env` and fill in the parameters:
```ini
GEMINI_API_KEY=AIzaSy...
GITHUB_TOKEN=ghp_...
GITHUB_REPOSITORY=owner/repository
GITHUB_PR_NUMBER=12
DRY_RUN=false
LOG_LEVEL=INFO
GEMINI_MODEL_NAME=gemini-2.5-flash
```

---

## 3. GitHub Actions Integration

To deploy the reviewer automatically to pull requests, commit the workflow file located at `.github/workflows/pr-reviewer.yml`.

### Secrets Setup
Add the following secret in your repository (**Settings** > **Secrets and variables** > **Actions**):
*   `GEMINI_API_KEY`: Your Gemini API key from Google AI Studio.

*(The GITHUB_TOKEN is automatically provided by GitHub runner on every workflow execution).*

### Permissions
Ensure the workflow runner has write permissions to post reviews. In **Settings** > **Actions** > **General** > **Workflow permissions**, select **Read and write permissions**.

---

## 4. Run Modes

### Local dry-run review (Safe Sandbox)
Run analysis on a PR but write output findings directly to the console instead of pushing comments to GitHub:
```bash
# In your .env file, ensure DRY_RUN=true
python -m src.main
```

### Full Remote execution
Process changes and submit inline review comments directly back to the pull request:
```bash
# In your .env file, ensure DRY_RUN=false
python -m src.main
```

---

## 5. Troubleshooting

*   **API 404 / Model Not Found**: If the Gemini API returns a 404 for a model, check the supported models for your API key. Older keys might not support newer default models. You can change the model by setting `GEMINI_MODEL_NAME=gemini-2.5-flash` or `GEMINI_MODEL_NAME=gemini-2.0-flash` in your configurations.
*   **API 422 on Comment Submission**: GitHub returns a 422 status if an inline comment tries to post to a line that is not part of the PR diff additions. The built-in validator handles this by checking coordinates, but ensure that your branch contains C# changes before opening a PR.
*   **Exit Codes Reference**:
    *   `0`: Successful review run completion.
    *   `2`: Configuration/missing environment variables error.
    *   `3`: API/Connection failure (rate limit timeouts, network issues).
    *   `4`: Core Review Engine exception.
    *   `1`: Unhandled generic system failure.