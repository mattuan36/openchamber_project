# Streamlit Starter

A compact Streamlit boilerplate with a secure `python-dotenv` setup, a
sidebar-driven control panel, a responsive column workspace, and session-state
caching for processed results.

## Quick start

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # then fill in real values
streamlit run app.py
```

## Layout

| File | Purpose |
| --- | --- |
| `app.py` | UI, processing logic, session-state cache |
| `.env.example` | Template for local configuration (safe to commit) |
| `.env` | Real local secrets (gitignored) |
| `requirements.txt` | Pinned dependency ranges |

## Environment pattern

- `.env` is loaded with `override=False`, so real process/CI variables always
  win over the file.
- Only `.env.example` is committed; `.env`, `.env.*`, and
  `.streamlit/secrets.toml` are ignored.
- Secrets are read server-side through `os.getenv` and never rendered or
  logged; the sidebar shows only whether a key is configured.

## Session-state cache

`get_results()` keys a cached `Results` object on the current input settings.
A rerun with unchanged settings reuses the stored result, while any input
change recomputes it and appends to the in-session run history. Use the
**Re-process now** button to force a fresh run.
