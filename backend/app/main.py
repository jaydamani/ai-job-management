from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, jobs, candidates, applications


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Gappeo API", version="1.0.0", lifespan=lifespan, root_path='/api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])


@app.get("/health")
async def health():
    return {"status": "ok"}
