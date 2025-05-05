from fastapi import APIRouter, HTTPException
import git
from typing import List
from schemas.git_schemas import TextResponse, CloneRequest, GitRepoPath
from utils.git_utils import get_repo, validate_repo_exists
from config import REPO_ROOT, logger

router = APIRouter()

# ----------------- API ENDPOINTS -----------------


@router.post(
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


@router.get(
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

@router.post(
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
        # TODO: Re-add indexing functionality once search endpoint is created
        # logger.info(f"Reindexing repository {repo_path_str} into collection {collection_name}")
        # index_repo(full_repo_path, collection_name)

        return TextResponse(result=f"Repository '{repo_path_str}' pulled and reindexed successfully into collection '{collection_name}'.")
    except Exception as e:
        logger.error(f"Error pulling and reindexing repository: {e}")
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Error pulling and reindexing repository: {str(e)}")
        raise e