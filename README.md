# Rounds Slack BI Bot

A Slack chatbot that answers analytics/BI questions about an apps portfolio. It converts natural language to SQL, executes against a simple schema, and returns either a short answer or a table. It also supports follow-ups, CSV export, and "show SQL".

## Features
- Natural-language questions -> SQL plan (LLM optional)
- Simple vs table answers with brief summaries/assumptions
- Follow-up context in the same thread (e.g., "what about iOS?")
- `/export` and "Export CSV" button reuse the last result (no re-query)
- "Show SQL" button returns the exact SQL used
- LangSmith tracing for observability
- SQLite demo DB with synthetic seed data; Postgres-ready

## Quick start (Windows-friendly)
1. **Clone & setup**
   ```powershell
   git clone <your-fork-url> rounds-slack-bi-bot
   cd rounds-slack-bi-bot
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   copy .env.example .env
   ```
   > If `copy` doesn't work in PowerShell, try: `Copy-Item .env.example .env`

2. **Create the demo DB**
   ```powershell
   python -m app.sql.seeds
   ```

3. **Configure Slack app**
   - Create an app at https://api.slack.com/apps
   - Scopes: `app_mentions:read`, `channels:history`, `chat:write`, `files:write`, `commands`
   - Enable Interactivity
   - Slash commands (examples): `/bi`, `/export`, `/sql`
   - **Dev mode: Socket Mode**
     - Enable Socket Mode and set the App Token
   - Add your Bot Token and App Token to `.env` (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`)

4. **Run (Socket Mode)**
   ```powershell
   python -m app.bolt_app
   ```

5. **(Optional) Run Events API server**
   - Set `APP_MODE=events` and provide `SLACK_SIGNING_SECRET`
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - Use your public URL for Event Subscriptions & Interactivity.

## Demo questions
- `@bot how many apps do we have?` → simple answer
- `@bot how many android apps do we have?`  
- `@bot what about ios?` → follow-up uses thread context
- `@bot which country generates the most revenue?` → table + brief summary
- `@bot List all iOS apps sorted by their popularity` → table; popularity = installs (last 30 days)
- `@bot Which apps had the biggest change in UA spend comparing Jan 2025 to Dec 2024?`
- `@bot export this as csv` or use the "Export CSV" button
- `@bot show me the SQL you used` or use the "Show SQL" button

## Architecture (MVP)
- **Slack Bolt** (Socket Mode by default), optional Events API via FastAPI
- **SQLite** for demo data (`data/rounds.db`)
- **LangChain + OpenAI** for NL→SQL planning; rules-based fallback if no API key
- **Pandas** for tabular formatting and CSV export
- In-thread **cache** to reuse last SQL & results

## Observability 
- If `LANGCHAIN_API_KEY` is set, LangSmith tracing is used. Otherwise it's a no-op.

## Repo layout
```
app/
  bolt_app.py          # Socket Mode app
  handlers.py          # Slack handlers
  main.py              # FastAPI entry for Events API 
  nlp/
    agent.py           # NL->SQL planning (LLM + fallback)
    prompts.py         # System & few-shot prompts
    schema_doc.py      # Schema doc string for prompting
  sql/
    schema.sql         # DDL
    seeds.py           # seed generator (python -m app.sql.seeds)
    runner.py          # safe SQL execution
  services/
    cache.py           # in-thread cache
    csv_export.py      # CSV save + Slack file upload
    formatting.py      # Slack table rendering
    authz.py           # very simple RBAC and SQL allowlist
  obs/
    tracing.py         # LangSmith 
data/                  # created at runtime (DB, exports)
dev/docker-compose.yml

## Notes
- This is a demo-grade project.  For production:
  - move to Postgres
  - persistent cache (Redis) + authz mapped to Slack user groups
  - more robust SQL safety & observability
  - charts (sparklines/bars) in Slack blocks
