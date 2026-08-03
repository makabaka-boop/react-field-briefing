from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import attachments, findings, meta, projects, reviews, sites, templates
from app.core.config import settings
from app.core.database import init_db
from app.core.errors import register_error_handlers


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    app.include_router(projects.router, prefix=settings.API_V1_PREFIX)
    app.include_router(sites.router, prefix=settings.API_V1_PREFIX)
    app.include_router(templates.router, prefix=settings.API_V1_PREFIX)
    app.include_router(findings.router, prefix=settings.API_V1_PREFIX)
    app.include_router(attachments.router, prefix=settings.API_V1_PREFIX)
    app.include_router(reviews.router, prefix=settings.API_V1_PREFIX)
    app.include_router(meta.router, prefix=settings.API_V1_PREFIX)

    @app.get("/")
    def root():
        return {"service": settings.APP_NAME, "status": "ok"}

    @app.on_event("startup")
    def on_startup():
        init_db()

    return app


app = create_app()
