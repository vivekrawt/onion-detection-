"""HTTP API and static site for the Allium onion classifier."""
import io
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .inference import APP_ROOT, CONFIDENCE_FLOOR, DEFAULT_MODEL, Engine, ModelError

STATIC_DIR = APP_ROOT / 'static'
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 80_000_000
log = logging.getLogger('allium')
engine = Engine()


@asynccontextmanager
async def lifespan(app):
    try:
        await run_in_threadpool(engine.warm_up, DEFAULT_MODEL)
    except ModelError as error:
        log.error('Default model unavailable: %s', error)
    yield


app = FastAPI(title='Allium', summary='Onion health classification', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.get('/', include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/api/models')
def models():
    return {'default_model': DEFAULT_MODEL, 'device': 'cpu', 'confidence_floor': CONFIDENCE_FLOOR,
            'models': engine.catalog()}


def decode_image(data):
    try:
        image = Image.open(io.BytesIO(data))
        if image.width * image.height > MAX_PIXELS:
            raise HTTPException(413, f'Image is too large; the limit is {MAX_PIXELS // 1_000_000} megapixels.')
        image.load()
    # Ultralytics patches Image.open to retry unknown files with the pi-heif plugin; ImportError means it is absent.
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError, ValueError, ImportError):
        raise HTTPException(400, 'That file could not be read as an image. Try a JPG, PNG, WEBP, BMP or HEIC photo.')
    return image


@app.post('/api/analyze')
async def analyze(file: UploadFile = File(...), model_id: str = Form(DEFAULT_MODEL)):
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f'Image is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.')
    if not data:
        raise HTTPException(400, 'The uploaded file is empty.')
    image = decode_image(data)
    try:
        result = await run_in_threadpool(engine.analyze, image, model_id)
    except ModelError as error:
        raise HTTPException(404 if model_id not in engine.specs else 503, str(error))
    result['image']['name'] = file.filename or 'image'
    return result
