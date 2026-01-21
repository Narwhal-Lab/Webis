"""
GitHub Code Download Plugin for Webis.
Downloads complete repository source code (based on student implementation).
"""

import logging
import os
import io
import zipfile
from typing import Iterator, Optional, Set

import requests

from webis.core.plugin import SourcePlugin
from webis.core.schema import WebisDocument, DocumentType, DocumentMetadata, PipelineContext

logger = logging.getLogger(__name__)

# Allowed code file extensions
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.ts', '.html', '.css', '.java', '.c', '.cpp',
    '.h', '.cs', '.go', '.rs', '.php', '.rb', '.swift', '.kt',
    '.md', '.txt', '.json', '.yaml', '.yml', '.sh', '.sql'
}

# Directories to ignore
IGNORE_DIRS = {
    'node_modules', 'venv', '.git', '.github', '__pycache__',
    'dist', 'build', 'target', 'bin', 'obj', '.idea', '.vscode'
}

# Max code size per repository (10MB)
MAX_CODE_SIZE = 10 * 1024 * 1024


class GitHubSearchPlugin(SourcePlugin):
    """
    Download complete GitHub repository source code.
    Downloads ZIP, extracts code files, and combines them into a single document.
    """

    name = "github"
    description = "Search and download complete GitHub repository source code"

    def fetch(
        self,
        query: str,
        limit: int = 3,
        context: Optional[PipelineContext] = None,
        **kwargs
    ) -> Iterator[WebisDocument]:

        url = "https://api.github.com/search/repositories"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Webis-Crawler"
        }

        # Use GitHub token if available
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"

        params = {"q": query, "per_page": limit, "sort": "stars"}

        try:
            logger.info(f"[GitHub] Searching: {query}")
            resp = requests.get(url, headers=headers, params=params, timeout=20)
            resp.raise_for_status()
            items = resp.json().get("items", [])

            if not items:
                logger.warning("[GitHub] No repositories found")
                return

            for repo in items:
                repo_full_name = repo['full_name']
                repo_name_safe = repo_full_name.replace("/", "_")

                # Download and process repository
                download_url = f"https://api.github.com/repos/{repo_full_name}/zipball"
                logger.info(f"[GitHub] Processing repo: {repo_full_name}")

                doc = self._download_and_extract_repo(
                    download_url,
                    repo_name_safe,
                    repo,
                    headers
                )

                if doc:
                    yield doc

        except Exception as e:
            logger.error(f"[GitHub] API error: {e}")

    def _download_and_extract_repo(
        self,
        url: str,
        repo_name: str,
        repo_meta: dict,
        headers: dict
    ) -> Optional[WebisDocument]:
        """
        Download ZIP and extract code files into a single document.
        """
        try:
            # Stream download ZIP
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()

                # Load ZIP into memory
                z = zipfile.ZipFile(io.BytesIO(r.content))

                readme_content = ""
                code_chunks = []
                total_size = 0

                # Process each file in ZIP
                for filename in z.namelist():
                    # Skip directories
                    if filename.endswith('/'):
                        continue

                    # Check if in ignored directory
                    parts = filename.split('/')
                    if any(p in IGNORE_DIRS for p in parts):
                        continue

                    base_name = os.path.basename(filename)
                    _, ext = os.path.splitext(base_name)
                    ext = ext.lower()

                    # Extract README separately
                    if base_name.lower() == 'readme.md':
                        try:
                            readme_content = z.read(filename).decode('utf-8', errors='ignore')
                        except:
                            pass
                        continue

                    # Extract code files
                    if ext in ALLOWED_EXTENSIONS:
                        try:
                            file_text = z.read(filename).decode('utf-8', errors='ignore')
                            file_size = len(file_text)

                            # Check size limit
                            if total_size + file_size > MAX_CODE_SIZE:
                                logger.warning(f"[GitHub] Size limit reached for {repo_name}")
                                code_chunks.append(f"\n\n[TRUNCATED: Remaining files omitted due to size limit]")
                                break

                            total_size += file_size

                            # Add file header
                            code_chunk = f"\n\n{'=' * 50}\nFILE PATH: {filename}\n{'=' * 50}\n{file_text}"
                            code_chunks.append(code_chunk)

                        except:
                            # Binary file incorrectly identified, skip
                            pass

            # Create combined content
            full_content = f"Repository: {repo_name}\n"
            if readme_content:
                full_content += f"\n{'=' * 50}\nREADME\n{'=' * 50}\n{readme_content}\n\n"

            full_content += f"{'=' * 50}\nSOURCE CODE\n{'=' * 50}\n"
            full_content += "".join(code_chunks)

            return WebisDocument(
                content=full_content,
                doc_type=DocumentType.HTML,  # Using HTML for rich text content
                meta=DocumentMetadata(
                    url=repo_meta.get("html_url"),
                    title=repo_meta.get("full_name"),
                    source_plugin=self.name,
                    custom={
                        "description": repo_meta.get("description"),
                        "stars": repo_meta.get("stargazers_count"),
                        "language": repo_meta.get("language"),
                        "code_size_bytes": total_size,
                        "files_extracted": len(code_chunks)
                    }
                )
            )

        except Exception as e:
            logger.error(f"[GitHub] Failed to process {repo_name}: {e}")
            return None
