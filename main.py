import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import i18n
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Translation setup
TRANSLATIONS_DIR = Path("translations")
SUPPORTED_LANGUAGES = ["en", "es", "fr"]
DEFAULT_LANGUAGE = "en"

def setup_i18n():
    """Initialize i18n configuration"""
    # Configure i18n
    i18n.set('filename_format', '{locale}.{format}')
    i18n.set('file_format', 'json')
    i18n.set('fallback', DEFAULT_LANGUAGE)
    i18n.set('locale', DEFAULT_LANGUAGE)
    i18n.set('enable_memoization', True)
    
    # Add translation files directory
    i18n.load_path.clear()
    i18n.load_path.append(str(TRANSLATIONS_DIR))

def parse_accept_language(accept_language: str) -> list[tuple[str, float]]:
    """Parse an ``Accept-Language`` header into ordered language options."""
    if not accept_language:
        return []

    languages: list[tuple[str, float]] = []
    for item in accept_language.split(','):
        cleaned = item.strip()
        if not cleaned:
            continue

        lang, _, quality_value = cleaned.partition(';q=')
        try:
            quality = float(quality_value) if quality_value else 1.0
        except ValueError:
            quality = 1.0

        languages.append((lang.strip().lower(), quality))

    return sorted(languages, key=lambda option: option[1], reverse=True)

def normalise_language(language: Optional[str]) -> Optional[str]:
    """Return a supported language code or ``None`` if unavailable."""
    if not language:
        return None

    language = language.lower()
    if language in SUPPORTED_LANGUAGES:
        return language

    if '-' in language:
        prefix = language.split('-', 1)[0]
        if prefix in SUPPORTED_LANGUAGES:
            return prefix

    return None


def detect_language(request: Request) -> str:
    """Pick the best matching language from the incoming request."""
    query_language = normalise_language(request.query_params.get("lang"))
    if query_language:
        return query_language

    header_language = request.headers.get("accept-language", "")
    for language, _ in parse_accept_language(header_language):
        selected = normalise_language(language)
        if selected:
            return selected

    return DEFAULT_LANGUAGE

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    os.makedirs(TRANSLATIONS_DIR, exist_ok=True)
    setup_i18n()
    yield
    # Shutdown (nothing to clean up in this demo)

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Internationalization Demo", 
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware


@app.middleware("http")
async def add_language_to_request(request: Request, call_next):
    """Attach the detected language to the request and mark the response."""
    language = detect_language(request)
    request.state.language = language

    response = await call_next(request)
    response.headers["Content-Language"] = language
    return response

# Response models
class WelcomeResponse(BaseModel):
    message: str
    language: str
    user_name: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    language: str

class CountResponse(BaseModel):
    message: str
    count: int
    language: str

class LanguageInfo(BaseModel):
    current_language: str
    supported_languages: list[str]
    message: str

@app.get("/", response_model=WelcomeResponse)
async def welcome(request: Request, name: Optional[str] = Query(None)):
    """Welcome endpoint with personalized greeting"""
    language = request.state.language
    
    if name:
        message = i18n.t('welcome_with_name', locale=language, name=name)
    else:
        message = i18n.t('welcome', locale=language)
    
    return WelcomeResponse(
        message=message,
        language=language,
        user_name=name
    )

@app.get("/hello", response_model=WelcomeResponse)
async def hello(request: Request):
    """Simple hello endpoint"""
    language = request.state.language
    
    return WelcomeResponse(
        message=i18n.t('hello', locale=language),
        language=language
    )

@app.get("/count/{number}", response_model=CountResponse)
async def count_items(request: Request, number: int):
    """Endpoint demonstrating pluralization"""
    language = request.state.language
    
    if number < 0:
        error_message = i18n.t('negative_number_error', locale=language)
        raise HTTPException(status_code=400, detail=error_message)
    
    # Use python-i18n's built-in pluralization
    message = i18n.t('item_count', locale=language, count=number)
    
    return CountResponse(
        message=message,
        count=number,
        language=language
    )

@app.get("/error-demo")
async def error_demo(request: Request):
    """Endpoint demonstrating localized error messages"""
    language = request.state.language
    
    error_message = i18n.t('error_demo', locale=language)
    
    return JSONResponse(
        status_code=400,
        content=ErrorResponse(
            error=error_message,
            language=language
        ).model_dump()
    )

@app.get("/language-info", response_model=LanguageInfo)
async def language_info(request: Request):
    """Get current language information"""
    language = request.state.language
    
    return LanguageInfo(
        current_language=language,
        supported_languages=SUPPORTED_LANGUAGES,
        message=i18n.t('language_info', locale=language)
    )

@app.get("/health")
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "supported_languages": SUPPORTED_LANGUAGES}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
