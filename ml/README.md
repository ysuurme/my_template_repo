# {{ project_name }}

{{ description }}

---

## Table of Contents

- [Quickstart](#quickstart)
- [Project Structure](#project-structure)

---

## Quickstart

Get up and running in under 2 minutes.

**1. Install dependencies**
```bash
uv sync
```

**2. Run the project**
```bash
uv run python main.py
```

**3. Run tests**
```bash
uv run pytest
```

**4. Generate a commit message from staged changes**
```bash
git add .
uv run commit-msg
```

---

## Project Structure

```
{{ project_name }}/
├── .env                          AI_PROVIDER, AI_API_KEY, AI_MODEL, LOG_LEVEL
├── main.py                       Entry point
├── src/
│   ├── config.py                 Centralized config (pydantic-settings, loads .env)
│   └── utils/
│       ├── m_log.py              Structured logger
│       └── m_commit.py           AI commit message generator
├── tests/                        Mirrors src/ hierarchy
└── .github/workflows/ci.yml      Lint + test on push/PR to main
```
