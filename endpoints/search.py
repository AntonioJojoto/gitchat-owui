from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, HTTPException
from schemas.git_schemas import IndexRequest
from retriever_qdrant import index_repo, search_repo
from config import REPO_ROOT, logger

router = APIRouter()

# ----------------- API ENDPOINTS -----------------

@router.post(
    "/index",
    description="Indexes the content of a specified Git repository into a search collection. Useful for making repository content searchable.",
    tags=["Search"],
)
async def index_repo_endpoint(request: IndexRequest):
    try:
        repo_path = (REPO_ROOT / request.repo_path).resolve()
        index_repo(repo_path,request.collection_name)
        return {"status": "success", "message": f"Indexed {request.repo_path} to {request.collection_name}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get(
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