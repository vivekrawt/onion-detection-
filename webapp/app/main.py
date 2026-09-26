"""HTTP API and static site for the Allium onion classifier."""
import io
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .inference import APP_ROOT, CONFIDENCE_FLOOR, DEFAULT_MODEL, Engine, ModelError
from .quality import QualityEngine, QUALITY_ID

STATIC_DIR = APP_ROOT / 'static'
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_PIXELS = 80_000_000
log = logging.getLogger('allium')
engine = Engine()
quality = QualityEngine(engine)


@asynccontextmanager
async def lifespan(app):
    try:
        await run_in_threadpool(engine.warm_up, DEFAULT_MODEL)
    except ModelError as error:
        log.error('Default model unavailable: %s', error)
    try:
        await run_in_threadpool(quality.warm_up)
    except ModelError as error:
        log.error('Quality model unavailable: %s', error)
    yield


app = FastAPI(title='Allium', summary='Onion health classification', lifespan=lifespan)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')


@app.get('/', include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / 'index.html', headers={'Cache-Control': 'no-cache'})


@app.get('/api/models')
def models():
    return {'default_model': QUALITY_ID, 'device': getattr(quality.classifier, 'device', 'cpu'), 'confidence_floor': CONFIDENCE_FLOOR,
            'models': [quality.catalog(), *engine.catalog()]}


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
async def analyze(file: UploadFile = File(...), model_id: str = Form(QUALITY_ID)):
    try:
        data = await file.read(MAX_UPLOAD_BYTES + 1)
    finally:
        await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f'Image is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.')
    if not data:
        raise HTTPException(400, 'The uploaded file is empty.')
    image = decode_image(data)
    try:
        if model_id == QUALITY_ID:
            result = await run_in_threadpool(quality.analyze, image)
        else:
            result = await run_in_threadpool(engine.analyze, image, model_id)
    except ModelError as error:
        raise HTTPException(404 if model_id not in engine.specs and model_id != QUALITY_ID else 503, str(error))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except Exception as error:
        log.exception('Analysis failed')
        raise HTTPException(500, 'Analysis could not finish. Please retry or choose a smaller lot.') from error
    result['image']['name'] = file.filename or 'image'
    return result


@app.get('/api/reports/{report_id}')
def report(report_id: UUID, download: bool = False):
    path = quality.store.directory(report_id) / 'report.pdf'
    if not path.is_file():
        raise HTTPException(404, 'Report not found. Analyze the image again.')
    return FileResponse(path, media_type='application/pdf', filename=f'allium-{report_id}.pdf',
                        content_disposition_type='attachment' if download else 'inline')


@app.get('/api/quality-assets/{report_id}/{filename}')
def quality_asset(report_id: UUID, filename: str):
    import re
    allowed = filename in {'source.jpg', 'analyzed.jpg'} or re.fullmatch(r'onion-[1-9][0-9]*\.jpg', filename)
    path = quality.store.directory(report_id) / filename
    if not allowed or not path.is_file():
        raise HTTPException(404, 'Image not found')
    return FileResponse(path, media_type='image/jpeg')
