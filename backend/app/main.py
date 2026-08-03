from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import init_db
from .errors import AppError, app_error_handler
from .routers import projects, sites, findings, templates, attachments, reviews, audit, overview, system_check

app = FastAPI(title="Field Briefing API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(sites.router, prefix="/api/v1", tags=["sites"])
app.include_router(findings.router, prefix="/api/v1", tags=["findings"])
app.include_router(templates.router, prefix="/api/v1", tags=["templates"])
app.include_router(attachments.router, prefix="/api/v1", tags=["attachments"])
app.include_router(reviews.router, prefix="/api/v1", tags=["reviews"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(overview.router, prefix="/api/v1", tags=["overview"])
app.include_router(system_check.router, prefix="/api/v1", tags=["system"])


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}
