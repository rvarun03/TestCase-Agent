# BRD-AGENT

Small FastAPI learning project: paste BRD text and receive structured test cases.
The Groq + LangChain integration is already wired up. It starts with one agent
so the integration is easy to understand before you build the four-agent version.

## Folder guide

| File | Purpose |
| --- | --- |
| `app/main.py` | FastAPI application and API endpoints |
| `app/config.py` | Reads the Groq key and model from `.env` |
| `app/models.py` | Defines validated request and response shapes |
| `app/agent.py` | LangChain connection, Groq model, and starter prompt |
| `LEARNING_PROMPT.md` | A single detailed prompt to learn the full future architecture with ChatGPT |
| `.env` | Your local secret configuration; Git ignores this file |

## Run it

```bash
cd BRD-AGENT
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev app/main.py
```

Open `http://127.0.0.1:8000/docs`, select `POST /api/testcases/generate`, then
use this example:

```json
{
  "brd_text": "A registered user can log in using email and password. After five incorrect password attempts, the account is locked."
}
```

## Before sharing the project

Never commit `.env` or paste its API key into chat, source code, or screenshots.
