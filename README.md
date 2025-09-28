# FastAPI Internationalization Demo

## How to run the app

Follow these steps to get the server running on your machine.

### 1. Install the dependencies

```bash
uv sync
```

If you do not have `uv` yet, install it with:

```bash
pip install uv
```

### 2. Start the development server

Run the app with auto-reload so changes show up right away:

```bash
uv run uvicorn main:app --reload --port 8000
```

This starts FastAPI on [http://localhost:8000](http://localhost:8000).

### 3. Try the endpoints

Open your browser at `http://localhost:8000/docs` to see the interactive docs.
You can also visit `http://localhost:8000/?lang=es` or `http://localhost:8000/?lang=fr`
to check the translated messages.

### Optional: use pip instead of uv

If you prefer plain `pip`, install the packages and run the server like this:

```bash
pip install -r requirements.txt
# or: pip install fastapi uvicorn python-i18n babel jinja2 pydantic starlette
uvicorn main:app --reload --port 8000
```

### Health check

FastAPI also exposes a simple health check at `http://localhost:8000/health`.
