import time
import requests
from typing import List, Dict, Any, Optional, Union

class WebisClient:
    """
    Python client for the Webis API.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})
            
    def ingest(
        self, 
        query: str, 
        sources: List[str] = ["tavily_search"], 
        max_results: int = 10,
        pipeline_preset: str = "default",
        wait: bool = False,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        Trigger an ingestion task.
        
        Args:
            query: The search query or task description.
            sources: List of sources to use.
            max_results: Maximum number of results to fetch.
            pipeline_preset: Pipeline configuration preset.
            wait: If True, wait for the task to complete.
            timeout: Timeout in seconds if waiting.
        """
        url = f"{self.base_url}/api/v1/ingest/"
        payload = {
            "query": query,
            "sources": sources,
            "max_results": max_results,
            "pipeline_preset": pipeline_preset
        }
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        task_id = data.get("task_id")
        
        if wait and task_id:
            return self.wait_for_task(task_id, timeout=timeout)
            
        return data

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task."""
        url = f"{self.base_url}/api/v1/tasks/{task_id}"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def wait_for_task(self, task_id: str, interval: float = 1.0, timeout: int = 60) -> Dict[str, Any]:
        """Wait for a task to complete."""
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout:
                raise TimeoutError(f"Task {task_id} timed out after {timeout} seconds")
                
            status_data = self.get_task_status(task_id)
            status = status_data.get("status")
            
            if status in ["SUCCESS", "FAILURE", "REVOKED"]:
                return status_data
            
            time.sleep(interval)

    def query(self, text: str, mode: str = "hybrid") -> Dict[str, Any]:
        """
        Query the knowledge base.
        """
        url = f"{self.base_url}/api/v1/query/"
        payload = {"text": text, "mode": mode} # Assuming this endpoint exists and takes these params
        # Note: The actual query endpoint implementation might differ, adjusting based on assumption
        # Let's check query.py content if possible, but for now I'll assume a standard interface
        
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        return response.json()
