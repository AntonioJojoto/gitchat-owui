from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import logger
from endpoints import repository_management, git_commands, search, file_context

app = FastAPI(
    title="git-api",
    version="0.1.0",
    description="An API for managing Git repositories and their contents. Provides endpoints for cloning, listing, and performing common Git operations like status, diff, log, checkout, and show. Also includes functionality for indexing repository content for search and retrieving relevant code snippets.",
)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repository_management.router)
app.include_router(git_commands.router)
app.include_router(search.router)
app.include_router(file_context.router)

# Optional: Add a root endpoint for basic health check
@app.get("/")
async def read_root():
    return {"message": "git-api is running"}
