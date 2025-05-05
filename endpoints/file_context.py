from fastapi import APIRouter, HTTPException
from fastapi import APIRouter, HTTPException
from schemas.git_schemas import FileContextRequest
from config import REPO_ROOT, logger

router = APIRouter()

# ----------------- API ENDPOINTS -----------------

@router.post(
    "/file_context",
    description="Provides the content of requested files.",
    tags=["File Context"],
)
async def get_file_context(request: FileContextRequest):
    file_contents = {}
    for file_path_str in request.file_paths:
        try:
            # Ensure the path is relative to the REPO_ROOT and within it
            full_file_path = (REPO_ROOT / file_path_str).resolve()

            # Basic security check: ensure the resolved path is within REPO_ROOT
            if not full_file_path.is_relative_to(REPO_ROOT):
                 raise HTTPException(status_code=400, detail=f"Invalid file path: {file_path_str}")

            if not full_file_path.is_file():
                 raise HTTPException(status_code=404, detail=f"File not found: {file_path_str}")

            with open(full_file_path, "r", encoding="utf-8") as f:
                file_contents[file_path_str] = f.read()
        except FileNotFoundError:
            file_contents[file_path_str] = f"Error: File not found at {file_path_str}"
        except Exception as e:
            file_contents[file_path_str] = f"Error reading file {file_path_str}: {str(e)}"
            logger.error(f"Error reading file {file_path_str}: {e}")

    return file_contents