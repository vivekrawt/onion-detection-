"""Run: python -m uvicorn backend.app.main:app --port 8001."""
from contextlib import asynccontextmanager
import logging
from threading import Lock
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from .config import settings
from .services.grading_service import GradingService
from .services.result_store import ResultStore
from .utils.image_utils import decode_image


class ReportRequest(BaseModel):
    report_id: UUID


def create_app(config=settings, classifier=None):
    @asynccontextmanager
    async def lifespan(app):
        # One model per worker. Use one worker on memory-limited systems.
        if classifier is None:
            from .models.clip_classifier import ClipClassifier
            app.state.classifier = await run_in_threadpool(ClipClassifier, config)
        else:
            app.state.classifier = classifier  # Dependency injection for offline tests only.
        app.state.store = ResultStore(config.OUTPUT_DIR)
        app.state.grader = GradingService(app.state.classifier, config)
        app.state.lock = Lock()
        yield

    app = FastAPI(title="Onion Quality Analyzer - CLIP Prototype", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ready", "model": config.CLIP_MODEL_NAME, "device": getattr(app.state.classifier, "device", "test")}

    def analyze_sync(data):
        image = decode_image(data, config.MAX_IMAGE_PIXELS)
        # Bound GPU work; reject concurrent inference rather than accumulating a queue.
        if not app.state.lock.acquire(blocking=False):
            raise HTTPException(503, "Analyzer busy; retry shortly")
        try:
            report_id = str(uuid4())
            directory = app.state.store.directory(report_id)
            directory.mkdir()
            result = app.state.grader.analyze(image, report_id, directory)
            app.state.store.save(result)
            return result
        finally:
            app.state.lock.release()

    @app.post("/analyze")
    async def analyze(image: UploadFile = File(...)):
        try:
            data = await image.read(config.MAX_UPLOAD_BYTES + 1)
        finally:
            await image.close()
        if len(data) > config.MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Image exceeds upload size limit")
        try:
            return await run_in_threadpool(analyze_sync, data)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        except HTTPException:
            raise
        except Exception as error:
            logging.exception("Onion analysis failed")
            raise HTTPException(500, "Analysis failed; inspect backend logs") from error

    @app.get("/analyses/{report_id}")
    def analysis(report_id: UUID):
        try:
            return app.state.store.load(report_id)
        except FileNotFoundError:
            raise HTTPException(404, "Analysis not found")

    @app.post("/generate-report")
    def report(request: ReportRequest):
        from .services.report_service import generate_report
        try:
            result = app.state.store.load(request.report_id)
        except FileNotFoundError:
            raise HTTPException(404, "Analysis not found")
        directory = app.state.store.directory(request.report_id)
        # Unique filename makes simultaneous requests safe.
        name = f"report-{uuid4()}.pdf"
        generate_report(result, directory / "analyzed.jpg", directory / name)
        return {"report_id": str(request.report_id), "pdf_url": f"/outputs/{request.report_id}/{name}"}

    @app.get("/outputs/{report_id}/{filename}")
    def artifact(report_id: UUID, filename: str):
        directory = app.state.store.directory(report_id)
        allowed = filename == "analyzed.jpg" or (filename.startswith("report-") and filename.endswith(".pdf"))
        allowed |= config.DEBUG and (filename == "mask.png" or (filename.startswith("onion-") and filename.endswith(".jpg")))
        if not allowed or PathGuard.invalid(filename) or not (directory / filename).is_file():
            raise HTTPException(404, "Artifact not found")
        return FileResponse(directory / filename, filename=filename)

    return app


class PathGuard:
    @staticmethod
    def invalid(filename):
        return any(character in filename for character in ("/", "\\", ":")) or ".." in filename


app = create_app()
