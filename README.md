# git-api

A FastAPI-based API for managing Git repositories and their contents. It provides endpoints for common Git operations and integrates with Qdrant for indexing repository content and enabling semantic search.

## Features:
*   Clone remote Git repositories.
*   List cloned repositories.
*   Perform standard Git operations: status, diff, log, checkout, show.
*   Index repository content for search using Qdrant.
*   Retrieve relevant code snippets using natural language queries.
*   Pull latest changes and reindex repositories.

## Technologies Used:
*   FastAPI
*   GitPython
*   Qdrant
*   Langchain
*   OpenAI Embeddings
*   Python

## Setup:
*   **Prerequisites:** Ensure you have Python, Git, and Docker (for running Qdrant) installed.
*   **Installation:**
    ```bash
    git clone <repository_url>
    cd git-api
    pip install -r requirements.txt # Assuming a requirements.txt file exists
    ```
*   **Running Qdrant:**
    ```bash
    docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
    ```
*   **Running the FastAPI application:**
    ```bash
    uvicorn main:app --reload
    ```

## API Endpoints:

### Repository Management
*   `POST /clone`: Clones a remote Git repository.
*   `GET /repos`: Lists cloned repositories.
*   `POST /pull_and_index`: Pulls latest changes and reindexes a repository.

### Git Operations
*   `POST /status`: Gets the current status of a repository.
*   `POST /diff`: Generates a diff.
*   `POST /log`: Retrieves commit history.
*   `POST /checkout`: Switches branches.
*   `POST /show`: Displays revision details.

### Search
*   `POST /index`: Indexes repository content for search.
*   `GET /retrieve`: Searches indexed content using a natural language query.
