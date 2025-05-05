import logging
from pathlib import Path
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