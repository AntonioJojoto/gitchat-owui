from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

import logging
from pathlib import Path
from typing import List, Optional
from enum import Enum
import git
from pydantic import BaseModel, Field, HttpUrl
from pathlib import Path

# Define la carpeta raíz donde se clonan/repos guardan
REPO_ROOT = Path("repos")
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
    description="An API to manage Git repositories with explicit endpoints, inputs, and outputs for better OpenAPI schemas.",
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
    DIFF_UNSTAGED = "diff_unstaged"
    DIFF_STAGED = "diff_staged"
    DIFF = "diff"
    COMMIT = "commit"
    ADD = "add"
    RESET = "reset"
    LOG = "log"
    CREATE_BRANCH = "create_branch"
    CHECKOUT = "checkout"
    SHOW = "show"
    INIT = "init"


# ----------------- MODELS -----------------


class GitRepoPath(BaseModel):
    repo_path: str = Field(..., description="File system path to the Git repository.")


class GitStatusRequest(GitRepoPath):
    pass


class GitDiffUnstagedRequest(GitRepoPath):
    pass


class GitDiffStagedRequest(GitRepoPath):
    pass


class GitDiffRequest(GitRepoPath):
    target: str = Field(..., description="The branch or commit to diff against.")


class GitCommitRequest(GitRepoPath):
    message: str = Field(..., description="Commit message for recording the change.")


class GitAddRequest(GitRepoPath):
    files: List[str] = Field(
        ..., description="List of file paths to add to the staging area."
    )


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


class FileListResponse(BaseModel):
    files: List[str] = Field(..., description="List of files in the repository")


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
    description="Clone a remote Git repository into the local repos directory",
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
    "/list_folder",
    response_model=FileListResponse,
    description="Recursively list all files and subfolders in a repository directory",
    tags=["File Operations"],
)
async def list_folder(
    repo_path: str = Query(..., description="Name of the repository folder under repos"),
    folder: str = Query(".", description="Relative folder path within the repository"),
):
    repo_base = validate_repo_exists(repo_path)
    base = repo_base / folder
    
    if not base.exists() or not base.is_dir():
        raise HTTPException(status_code=404, detail=f"Folder not found: {folder}")
    
    try:
        files = [p.relative_to(repo_base).as_posix() for p in base.rglob("*")]
        return FileListResponse(files=files)
    except Exception as e:
        logger.error(f"Error listing folder: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing folder: {str(e)}")


@app.get(
    "/repos",
    response_model=List[str],
    description="List all cloned repositories",
    tags=["Repository Management"],
)
async def list_repos():
    """Return a list of all repository folder names under repos directory."""
    try:
        return [p.name for p in REPO_ROOT.iterdir() if p.is_dir()]
    except Exception as e:
        logger.error(f"Error listing repositories: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing repositories: {str(e)}")


@app.get(
    "/read_file",
    response_model=TextResponse,
    description="Read the contents of a file in a repository",
    tags=["File Operations"],
)
async def read_file(
    repo_path: str = Query(..., description="Name of the repository folder under repos"),
    file: str = Query(..., description="Relative file path within the repository"),
):
    repo_base = validate_repo_exists(repo_path)
    f = repo_base / file
    
    if not f.exists() or not f.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {file}")
    
    try:
        content = f.read_text(encoding="utf-8")
        return TextResponse(result=content)
    except UnicodeDecodeError:
        # Try to read as binary and return notice for binary files
        try:
            f.read_bytes()
            return TextResponse(result="[Binary file, content cannot be displayed]")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error reading binary file: {str(e)}")
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")


@app.post(
    "/status",
    response_model=TextResponse,
    description="Get the current status of the Git repository.",
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
    "/diff_unstaged",
    response_model=TextResponse,
    description="Get differences of unstaged changes.",
    tags=["Git Operations"],
)
async def diff_unstaged(request: GitDiffUnstagedRequest):
    try:
        repo = get_repo(request.repo_path)
        diff = repo.git.diff()
        return TextResponse(result=diff)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error getting unstaged diff: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting unstaged diff: {str(e)}")
        raise e


@app.post(
    "/diff_staged",
    response_model=TextResponse,
    description="Get differences of staged changes.",
    tags=["Git Operations"],
)
async def diff_staged(request: GitDiffStagedRequest):
    try:
        repo = get_repo(request.repo_path)
        diff = repo.git.diff("--cached")
        return TextResponse(result=diff)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error getting staged diff: {e}")
            raise HTTPException(status_code=500, detail=f"Error getting staged diff: {str(e)}")
        raise e


@app.post(
    "/diff",
    response_model=TextResponse,
    description="Get comparison between two branches or commits.",
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
    "/commit",
    response_model=TextResponse,
    description="Commit staged changes to the repository.",
    tags=["Git Operations"],
)
async def commit_changes(request: GitCommitRequest):
    try:
        repo = get_repo(request.repo_path)
        commit = repo.index.commit(request.message)
        return TextResponse(result=f"Committed changes with hash {commit.hexsha}")
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error committing changes: {e}")
            raise HTTPException(status_code=500, detail=f"Error committing changes: {str(e)}")
        raise e


@app.post(
    "/add", 
    response_model=TextResponse, 
    description="Stage files for commit.",
    tags=["Git Operations"],
)
async def add_files(request: GitAddRequest):
    try:
        repo = get_repo(request.repo_path)
        repo.index.add(request.files)
        return TextResponse(result="Files staged successfully.")
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error staging files: {e}")
            raise HTTPException(status_code=500, detail=f"Error staging files: {str(e)}")
        raise e


@app.post(
    "/reset", 
    response_model=TextResponse, 
    description="Unstage all staged changes.",
    tags=["Git Operations"],
)
async def reset_changes(request: GitResetRequest):
    try:
        repo = get_repo(request.repo_path)
        repo.index.reset()
        return TextResponse(result="All staged changes reset.")
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error resetting changes: {e}")
            raise HTTPException(status_code=500, detail=f"Error resetting changes: {str(e)}")
        raise e


@app.post(
    "/log",
    response_model=LogResponse,
    description="Get recent commit history of the repository.",
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
    "/create_branch", 
    response_model=TextResponse, 
    description="Create a new branch.",
    tags=["Git Operations"],
)
async def create_branch(request: GitCreateBranchRequest):
    try:
        repo = get_repo(request.repo_path)
        if request.base_branch is None:
            base_branch = repo.active_branch
        else:
            try:
                base_branch = repo.refs[request.base_branch]
            except IndexError:
                raise HTTPException(
                    status_code=404, detail=f"Base branch '{request.base_branch}' not found"
                )
                
        repo.create_head(request.branch_name, base_branch)
        return TextResponse(
            result=f"Created branch '{request.branch_name}' from '{base_branch}'."
        )
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error creating branch: {e}")
            raise HTTPException(status_code=500, detail=f"Error creating branch: {str(e)}")
        raise e


@app.post(
    "/checkout", 
    response_model=TextResponse, 
    description="Checkout an existing branch.",
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
    description="Show details and diff of a specific commit.",
    tags=["Git Operations"],
)
async def show_revision(request: GitShowRequest):
    try:
        repo = get_repo(request.repo_path)
        try:
            commit = repo.commit(request.revision)
        except git.BadName:
            raise HTTPException(
                status_code=404, detail=f"Revision '{request.revision}' not found"
            )
            
        details = (
            f"Commit: {commit.hexsha}\n"
            f"Author: {commit.author}\n"
            f"Date: {commit.authored_datetime}\n"
            f"Message: {commit.message.strip()}\n"
        )
        
        # Handle first commit case (no parents)
        if commit.parents:
            diff = commit.diff(commit.parents[0], create_patch=True)
        else:
            diff = commit.diff(git.NULL_TREE, create_patch=True)
            
        diff_text = "\n".join(d.diff.decode("utf-8") for d in diff)
        return TextResponse(result=details + "\n" + diff_text)
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Error showing revision: {e}")
            raise HTTPException(status_code=500, detail=f"Error showing revision: {str(e)}")
        raise e


@app.post(
    "/init", 
    response_model=TextResponse, 
    description="Initialize a new Git repository.",
    tags=["Repository Management"],
)
async def init_repo(request: GitInitRequest):
    try:
        repo = git.Repo.init(path=request.repo_path, mkdir=True)
        return TextResponse(
            result=f"Initialized empty Git repository at '{repo.git_dir}'"
        )
    except Exception as e:
        logger.error(f"Error initializing repository: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing repository: {str(e)}")
