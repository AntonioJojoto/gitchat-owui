from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl

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

class FileContextRequest(BaseModel):
    file_paths: List[str] = Field(..., description="List of file paths relative to the repository root.")