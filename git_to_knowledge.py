import os
import requests
import git
import json
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except ImportError:
    print("dotenv not installed, skipping...")

# Global configuration
WEBUI_URL = os.getenv("WEBUI_URL", "https://ai.antonioaslan.com")
TOKEN = os.getenv("TOKEN")
MODEL = os.getenv("MODEL")

def add_file_to_knowledge(knowledge_id: str, file_path: str, display_name: str) -> Dict[str, Any]:
    """
    Modified version supporting display names
    """
    url = f'{WEBUI_URL}/api/v1/knowledge/{knowledge_id}/file/add'
    headers = {'Authorization': f'Bearer {TOKEN}'}
    
    with open(file_path, 'rb') as f:
        files = {'file': (display_name, f)}
        response = requests.post(url, headers=headers, files=files)
    
    if not response.ok:
        raise Exception(f"Upload failed: {response.text}")
    return response.json()

def clone_github_repo(repo_url: str, base_dir: str = "repos") -> str:
    """
    Clone a GitHub repository into a /repos folder, creating it if needed.
    
    Args:
        repo_url: GitHub repository URL (e.g., "https://github.com/user/repo.git")
        base_dir: Parent directory for repositories (default: "repos")
    
    Returns:
        str: Path to the cloned repository
    
    Raises:
        git.GitCommandError: If cloning fails
        OSError: If directory creation fails
    """
    repos_path = Path(base_dir)
    repos_path.mkdir(parents=True, exist_ok=True)
    
    repo_name = repo_url.rstrip("/").split("/")[-1]
    if repo_name.endswith(".git"):
        repo_name = repo_name[:-4]
    
    repo_path = repos_path / repo_name
    if repo_path.exists():
        return f"Repository already exists at: {repo_path}"
    
    git.Repo.clone_from(repo_url, str(repo_path))
    return f"Repository cloned to: {repo_path}"

def upload_file(file_path: str) -> Dict[str, Any]:
    url = f'{WEBUI_URL}/api/v1/files/'
    headers = {
        'Authorization': f'Bearer {TOKEN}',
        'Accept': 'application/json'
    }
    files = {'file': open(file_path, 'rb')}
    response = requests.post(url, headers=headers, files=files)
    return response.json()

def add_to_knowledge(knowledge_id: str, file_id: str) -> Dict[str, Any]:
    """Step 2: Add to knowledge base"""
    response = requests.post(
        f'{WEBUI_URL}/api/v1/knowledge/{knowledge_id}/file/add',
        headers={'Authorization': f'Bearer {TOKEN}'},
        json={'file_id': file_id}
    )
    return response.json()

def should_skip_file(path: Path) -> bool:
    return (not path.is_file() or 
            ".git" in path.parts or 
            path.name.startswith("."))

def get_file_commit(repo: git.Repo, rel_path: str) -> str:
    return repo.git.log('-1', '--pretty=format:%H', '--', str(rel_path))

def needs_upload(metadata: Dict[str, Any], rel_path: str, current_commit: str) -> bool:
    existing = metadata.get(rel_path)
    return not existing or existing['file_commit'] != current_commit

def load_metadata(storage_file: str) -> Dict[str, Any]:
    return json.load(open(storage_file)) if Path(storage_file).exists() else {}

def save_metadata(data: Dict[str, Any], storage_file: str):
    with open(storage_file, 'w') as f:
        json.dump(data, f, indent=2)

def upload_repo_to_knowledge(repo_path: str, knowledge_id: str, storage_file: str = "file_metadata.json") -> None:
    """
    Full repo processor with metadata tracking:
    - Excludes .git/
    - Uses flattened filenames (folder_file.ext)
    - Tracks file_ids and Git commits
    - Saves metadata for deletion
    """
    repo = git.Repo(repo_path)
    current_commit = repo.head.commit.hexsha
    metadata = load_metadata(storage_file)

    for item in Path(repo_path).rglob('*'):
        if should_skip_file(item):
            continue

        rel_path = item.relative_to(repo_path)
        flat_name = "_".join(rel_path.parts)
        file_commit = get_file_commit(repo, rel_path)

        if not needs_upload(metadata, str(rel_path), file_commit):
            continue

        try:
            uploaded = upload_file(item)
            kb_response = add_to_knowledge(knowledge_id, uploaded['id'])
            
            metadata[str(rel_path)] = {
                "file_id": uploaded['id'],
                "kb_entry_id": kb_response.get('entry_id'),
                "flat_name": flat_name,
                "knowledge_id": knowledge_id,
                "file_commit": file_commit,
                "repo_commit": current_commit,
                "last_upload": 1
            }

        except Exception as e:
            print(f"❌ Failed {rel_path}: {str(e)}")
            continue

    save_metadata(metadata, storage_file)
