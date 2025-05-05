from fastapi import APIRouter, HTTPException
import git
from typing import List
from schemas.git_schemas import TextResponse, LogResponse, GitStatusRequest, GitDiffRequest, GitLogRequest, GitCheckoutRequest, GitShowRequest
from utils.git_utils import get_repo
from config import logger

router = APIRouter()

# ----------------- API ENDPOINTS -----------------

@router.post(
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


@router.post(
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


@router.post(
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


@router.post(
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


@router.post(
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