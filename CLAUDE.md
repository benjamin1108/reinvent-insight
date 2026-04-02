# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run
- **Install Dependencies**: `pip install -e .`
- **Start Dev Server**: `./run-dev.sh` (Runs on http://localhost:8002)
- **Start Prod Server**: `reinvent-insight web --host 0.0.0.0 --port 8001`
- **CLI Usage**: `reinvent-insight --help`
- **Install Fonts**: `./scripts/install_chinese_fonts.sh` (Required for PDF generation)

## Testing & Linting
- **Run Python Tests**: `pytest`
- **Lint Python**: `ruff check .`
- **Format Python**: `ruff format .`
- **Frontend Tests**: Open files in `web/test/` directly in browser (e.g., `web/test/test-toast.html`).

## Architecture
- **Backend**: Python 3.9+, FastAPI, Asyncio.
  - **Layered Structure**:
    - `api/`: HTTP endpoints and schemas.
    - `core/`: Config, logging, error handling.
    - `domain/`: Business models, prompts, workflows.
    - `infrastructure/`: External services (AI clients, YouTube downloader).
    - `services/`: Business logic and task management.
- **Frontend**: Vue 3 (No-Build/Native ES Modules).
  - **Core**: `component-loader.js` (dynamic loading), `event-bus.js`.
  - **Components**: `web/components/` (HTML/CSS/JS separated).
- **Storage**:
  - `downloads/subtitles`: Raw subtitles.
  - `downloads/summaries`: Generated markdown reports.
  - `downloads/tasks`: Task state cache.

## Style & Conventions
- **Language**: Use **Chinese** for all comments, commit messages, and thinking processes.
- **Frontend**:
  - Do NOT use build tools (Webpack/Vite). Keep using native ES modules.
  - Components must be split into `.js`, `.html`, `.css` in `web/components/`.
- **Backend**:
  - Use `async/await` for I/O operations.
  - Follow the established layered architecture; do not mix infrastructure code into domain logic.
