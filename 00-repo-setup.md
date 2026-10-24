Build Sheet 00 --- Repository Setup
=================================

**Project:** One Bad Tuesday (working name)\
**Goal:** Initialize a clean, runnable monorepo for the HackTX project. **This build sheet is for setup only.** Do not implement the financial engine, Nessie data ingestion, crisis graph, SerpApi research agent, or plan optimizer yet.

Instructions for the coding agent
---------------------------------

You are responsible for choosing a sensible, minimal repository structure and creating the necessary files. Do **not** expect a pre-made folder tree or generate a large amount of boilerplate. Favor the fastest maintainable setup for a 24-hour hackathon.

### 1\. Initialize the project

-   Set up a **Next.js + TypeScript** frontend, using the App Router and Tailwind CSS.
-   Set up a **Python FastAPI** backend.
-   Keep frontend and backend in one repository, with clear separation and simple local development commands.
-   Use standard package/dependency management for each stack. Pin or lock dependencies where practical.
-   Add a root `README.md` with exact install and run instructions for macOS and Windows (PowerShell where commands differ).
-   Configure Git and a useful `.gitignore` for Node, Python, build outputs, editor files, and environment secrets. If Git is already initialized, preserve the existing history and configuration.
-   Do not create or push a GitHub remote without asking for the desired repository name/account and permission.

### 2\. Set up environment variables and API credentials

The app will later integrate **Capital One Nessie**, **SerpApi**, and **one LLM provider**.

-   Create documented `.env.example` templates containing **placeholder names only** (no real credentials). Use backend-specific and frontend-specific env files if appropriate.
-   Keep Nessie, SerpApi, and LLM API keys on the **backend only**. Never expose secrets through `NEXT_PUBLIC_*` variables or frontend code.
-   Include placeholders for `NESSIE_API_KEY`, `SERPAPI_API_KEY`, and an LLM API key plus any necessary base URL/model configuration. Choose the provider **only after asking me** which one to use.
-   **Ask me for the required API credentials/configuration when you reach the integration setup**, explain exactly where to place them locally, and don't print, commit, or repeat secret values. If I don't have keys yet, continue setup with empty placeholders; do not invent credentials.
-   Load and validate configuration cleanly, with useful error messages for missing values. The app should still start locally without optional integration keys, and clearly indicate that external integrations aren't configured.
-   Ensure actual `.env` files, credentials, and private tokens are Git-ignored; commit only `.env.example` templates.

### 3\. Establish a working local development loop

-   Create a minimal frontend landing page showing the working project title and a simple **backend connection/health** status.
-   Add a backend `GET /health` endpoint returning a small JSON success response.
-   Configure frontend-to-backend communication for local development (including CORS or a proxy as appropriate).
-   Provide easy commands for running frontend and backend concurrently. A root helper script is fine, but keep the setup lightweight.
-   Add basic formatting/linting and at least one small backend health test. Add a frontend typecheck/build check.

### 4\. Document the foundation

-   Write a concise `README.md` covering prerequisites, setup, environment variables, local URLs, commands, tests, and troubleshooting.
-   Create `docs/DECISIONS.md` to log material architectural choices and why they were made.
-   Leave a clear place for later build sheets/specifications, but **do not implement their features** in this phase.
-   Explain any assumptions you made rather than silently selecting substantial services or paid infrastructure.

### 5\. Verify before calling setup complete

Run the available checks and report their actual results:

-   Backend dependencies install and FastAPI starts.
-   `GET /health` responds successfully.
-   Frontend dependencies install and the Next.js app starts.
-   Frontend can reach the backend health endpoint.
-   Backend tests pass; frontend typecheck/lint/build checks pass.
-   `.env` and credential files are ignored by Git.

If something cannot be verified in your environment, say exactly what was not tested and what command I should run locally. **Never claim an unrun test passed.**

Definition of done
------------------

I can clone/open the repository, follow the README, start both services locally, and see a basic page with a working backend health check. The repo is ready for the next build sheets without having implemented their functionality.

**When finished:** Summarize the files created, commands to run, checks performed, any missing credentials, and questions requiring my decision. Then **stop** and wait for the next build sheet.