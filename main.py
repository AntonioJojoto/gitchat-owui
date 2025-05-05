from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

import logging
from pathlib import Path
from typing import List, Optional
from enum import Enum
import git
from pydantic import BaseModel, Field, HttpUrl
from pathlib import Path


from retriever_qdrant import index_repo, search_repo
from pathlib import Path
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()
# Define la carpeta raíz donde se clonan/repos guardan
REPO_ROOT = Path.home() / "repos"
REPO_ROOT.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("git-api")

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


# ----------------- ENUMS -----------------


class GitTools(str, Enum):
    STATUS = "status"
    DIFF = "diff"
    COMMIT = "commit"
    LOG = "log"
    CHECKOUT = "checkout"
    SHOW = "show"
    INIT = "init"


# ----------------- MODELS -----------------

class IndexRequest(BaseModel):
    repo_path: str
    collection_name: str

class GitRepoPath(BaseModel):
    repo_path: str = Field(..., description="File system path to the Git repository.")


class GitStatusRequest(GitRepoPath):
    pass


class GitDiffRequest(GitRepoPath):
    target: str = Field(..., description="The branch or commit to diff against.")


class GitCommitRequest(GitRepoPath):
    message: str = Field(..., description="Commit message for recording the change.")



class GitResetRequest(GitRepoPath):
    pass


class GitLogRequest(GitRepoPath):
    max_count: int = Field(10, description="Maximum number of commits to retrieve.")


class GitCreateBranchRequest(GitRepoPath):
    branch_name: str = Field(..., description="Name of the branch to create.")
    base_branch: Optional[str] = Field(
        None, description="Optional base branch name to create the new branch from."
    )


class GitCheckoutRequest(GitRepoPath):
    branch_name: str = Field(..., description="Branch name to checkout.")


class GitShowRequest(GitRepoPath):
    revision: str = Field(
        ..., description="The commit hash or branch/tag name to show."
    )


class GitInitRequest(GitRepoPath):
    pass


class TextResponse(BaseModel):
    result: str = Field(..., description="Description of the operation result.")


class LogResponse(BaseModel):
    commits: List[str] = Field(
        ..., description="A list of formatted commit log entries."
    )


class CloneRequest(BaseModel):
    repo_url: HttpUrl = Field(..., description="URL of the remote repo (HTTPS).")



# ----------------- UTILITY FUNCTIONS -----------------


def get_repo(repo_path: str) -> git.Repo:
    """
    Get a Git repository object from a path.
    
    Args:
        repo_path: Path to the Git repository
        
    Returns:
        git.Repo: The repository object
        
    Raises:
        HTTPException: If the repository is invalid
    """
    full_path = REPO_ROOT / repo_path if not repo_path.startswith("/") else Path(repo_path)
    
    try:
        return git.Repo(full_path)
    except git.InvalidGitRepositoryError:
        raise HTTPException(
            status_code=400, detail=f"Invalid Git repository at '{full_path}'"
        )
    except Exception as e:
        logger.error(f"Error accessing repository: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error accessing repository: {str(e)}"
        )


def validate_repo_exists(repo_path: str) -> Path:
    """
    Validate that a repository exists.
    
    Args:
        repo_path: Name of the repository folder under repos
        
    Returns:
        Path: Path to the repository
        
    Raises:
        HTTPException: If the repository does not exist
    """
    path = REPO_ROOT / repo_path
    if not path.exists() or not path.is_dir():
        raise HTTPException(
            status_code=404, detail=f"Repository not found: {repo_path}"
        )
    return path


# ----------------- API ENDPOINTS -----------------


@app.post(
    "/clone",
    response_model=TextResponse,
    description="Clones a remote Git repository specified by a URL into the local 'repos' directory. Useful for adding new repositories to the system for management and indexing.",
    tags=["Repository Management"],
)
async def clone_repo(request: CloneRequest):
    repo_url = str(request.repo_url)
    name = repo_url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    dest = REPO_ROOT / name
    
    if dest.exists():
        return TextResponse(result=f"Repository '{name}' already exists")
    
    try:
        logger.info(f"Cloning repository {repo_url} to {dest}")
        git.Repo.clone_from(repo_url, str(dest))
        return TextResponse(result=f"Repository cloned into '{name}'")
    except Exception as e:
        logger.error(f"Error cloning repository: {e}")
        raise HTTPException(status_code=500, detail=f"Error cloning repository: {str(e)}")


@app.get(
    "/repos",
    response_model=List[str],
    description="Retrieves a list of the names of all Git repositories that have been cloned into the local 'repos' directory. Useful for identifying available repositories.",
    tags=["Repository Management"],
)
async def list_repos():
    """Return a list of all repository folder names under repos directory."""
    try:
        return [p.name for p in REPO_ROOT.iterdir() if p.is_dir()]
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing repositories: {str(e)}")


@app.post(
    "/status",
    response_model=TextResponse,
    description="Gets the current status of a specified Git repository, including information about modified, added, and untracked files. Requires the path to the repository.",
    tags=["Git Operations"],
)
async def get_status(request: GitStatusRequest):
    try:
        repo = get_repo(request.repo_path)
        status = repo.git.status()
        return TextResponse(result=status)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error getting repository status: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting repository status: {str(e)}")
        raise e


@app.post(
    "/diff",
    response_model=TextResponse,
    description="Generates a diff showing the differences between the current state of a repository and a specified target (branch or commit). Requires the repository path and the target for comparison.",
    tags=["Git Operations"],
)
async def diff_target(request: GitDiffRequest):
    try:
        repo = get_repo(request.repo_path)
        diff = repo.git.diff(request.target)
        return TextResponse(result=diff)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error getting diff: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting diff: {str(e)}")
        raise e


@app.post(
    "/log",
    response_model=LogResponse,
    description="Retrieves the recent commit history for a specified Git repository. Can be limited by the maximum number of commits. Requires the repository path.",
    tags=["Git Operations"],
)
async def get_log(request: GitLogRequest):
    try:
        repo = get_repo(request.repo_path)
        commits = [
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message.strip()}\n"
            for commit in repo.iter_commits(max_count=request.max_count)
        ]
        return LogResponse(commits=commits)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error getting commit log: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting commit log: {str(e)}")
        raise e


@app.post(
    "/checkout", 
    response_model=TextResponse, 
    description="Switches the current branch of a specified Git repository to an existing branch. Requires the repository path and the name of the branch to checkout.",
    tags=["Git Operations"],
)
async def checkout_branch(request: GitCheckoutRequest):
    try:
        repo = get_repo(request.repo_path)
        try:
            repo.git.checkout(request.branch_name)
            return TextResponse(result=f"Switched to branch '{request.branch_name}'.")
        except git.GitCommandError as e:
            if "did not match any file(s) known to git" in str(e):
                raise HTTPException(
                    status_code=404, detail=f"Branch '{request.branch_name}' not found"
                )
            raise e
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error checking out branch: {e}")
            raise HTTPException(status_code=500, detail=f"Error checking out branch: {str(e)}")
        raise e


@app.post(
    "/show",
    response_model=TextResponse,
    description="Displays the details and diff of a specific commit or revision in a Git repository. Requires the repository path and the commit hash or revision name.",
    tags=["Git Operations"],
)
async def show_revision(request: GitShowRequest):
    try:
        repo = get_repo(request.repo_path)
        try:
            show = repo.git.show(request.revision)
            return TextResponse(result=show)
        except git.GitCommandError as e:
            if "unknown revision or path" in str(e):
                raise HTTPException(
                    status_code=404, detail=f"Revision '{request.revision}' not found"
                )
            raise e
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error showing revision: {e}")
            raise HTTPException(status_code=500, detail=f"Error showing revision: {str(e)}")
        raise e


@app.post(
    "/index",
    description="Indexes the content of a specified Git repository into a search collection. Useful for making repository content searchable.",
)
async def index_repo_endpoint(request: IndexRequest):
    try:
        repo_path = (REPO_ROOT / request.repo_path).resolve()
        index_repo(repo_path,request.collection_name)
        return {"status": "success", "message": f"Indexed {request.repo_path} to {request.collection_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get(
    "/retrieve",
    description="Searches a specified indexed repository collection using a natural language query and retrieves relevant code snippets. Useful for finding code related to a specific topic or function.",
    tags=["Search"],
)
async def retrieve(query: str, collection_name: str):
    try:
        results = search_repo(query, collection_name)
        return {"results": results}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post(
    "/pull_and_index",
    response_model=TextResponse,
    description="Pulls the latest changes from the remote origin for a specified Git repository and then reindexes its content. Ensures the search index is up-to-date with the latest code.",
    tags=["Repository Management"],
)
async def pull_and_index_repo(request: GitRepoPath):
    try:
        repo_path_str = request.repo_path
        full_repo_path = REPO_ROOT / repo_path_str if not repo_path_str.startswith("/") else Path(repo_path_str)

        # Validate repository exists
        validate_repo_exists(repo_path_str)

        repo = get_repo(repo_path_str)
        
        logger.info(f"Pulling latest changes for repository at {full_repo_path}")
        origin = repo.remotes.origin
        origin.pull()

        # Use the repository name as the collection name for indexing
        collection_name = full_repo_path.name
        logger.info(f"Reindexing repository {repo_path_str} into collection {collection_name}")
        index_repo(full_repo_path, collection_name)

        return TextResponse(result=f"Repository '{repo_path_str}' pulled and reindexed successfully into collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Error pulling and reindexing repository: {e}")
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Error pulling and reindexing repository: {str(e)}")
        raise e
