import os
import re
import i18n
from typing import Optional
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Query, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
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
    """Parse Accept-Language header with q-values"""
    languages = []
    if not accept_language:
        return languages
    
    for item in accept_language.split(','):
        item = item.strip()
        if ';q=' in item:
            lang, quality = item.split(';q=', 1)
            try:
                quality = float(quality.strip())
            except ValueError:
                quality = 1.0
        else:
            lang = item
            quality = 1.0
        
        lang = lang.strip().lower()
        languages.append((lang, quality))
    
    # Sort by quality (highest first)
    languages.sort(key=lambda x: x[1], reverse=True)
    return languages

class I18nMiddleware(BaseHTTPMiddleware):
    """Middleware to detect and set user language preference"""
    
    async def dispatch(self, request: Request, call_next):
        # Check for language in query parameter first
        lang = request.query_params.get("lang")
        if lang:
            lang = lang.lower()
        
        # If not in query params, check Accept-Language header
        if not lang or lang not in SUPPORTED_LANGUAGES:
            accept_language = request.headers.get("accept-language", "")
            if accept_language:
                # Parse Accept-Language header with q-values
                parsed_languages = parse_accept_language(accept_language)
                for language, _ in parsed_languages:
                    # Check for exact match
                    if language in SUPPORTED_LANGUAGES:
                        lang = language
                        break
                    # Check for language prefix (e.g., en-US -> en)
                    elif '-' in language:
                        prefix = language.split('-')[0]
                        if prefix in SUPPORTED_LANGUAGES:
                            lang = prefix
                            break
        
        # Default to English if no valid language found
        if not lang or lang not in SUPPORTED_LANGUAGES:
            lang = DEFAULT_LANGUAGE
        
        # Store language in request state for response metadata
        request.state.language = lang
        
        response = await call_next(request)
        
        # Add Content-Language header to response
        response.headers["Content-Language"] = lang
        
        return response

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
app.add_middleware(I18nMiddleware)

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