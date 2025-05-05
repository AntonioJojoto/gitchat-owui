from fastapi import HTTPException
import git
import logging
from pathlib import Path
from config import REPO_ROOT

logger = logging.getLogger("git-api")

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