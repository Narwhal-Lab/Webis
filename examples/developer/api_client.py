"""
API Integration Example

This example demonstrates how to integrate Webis into your application using the API.
"""
import asyncio
import httpx
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class WebisAPIClient:
    """Simple Webis API client for integration"""

    base_url: str
    api_key: str
    timeout: int = 30

    def __post_init__(self):
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=self.timeout
        )

    async def run_pipeline(self, query: str, **kwargs) -> Dict[str, Any]:
        """Execute a pipeline"""
        response = await self.client.post(
            "/api/v1/ingest/",
            json={
                "query": query,
                **kwargs
            }
        )
        response.raise_for_status()
        return response.json()

    async def extract_data(self, file_path: str, task: str, **kwargs) -> Dict[str, Any]:
        """Extract data from a file"""
        with open(file_path, 'rb') as f:
            files = {'file': (file_path, f, 'application/octet-stream')}
            data = {'task': task, **kwargs}

            response = await self.client.post(
                "/api/v1/extract/",
                data=data,
                files=files
            )
        response.raise_for_status()
        return response.json()

    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get task status"""
        response = await self.client.get(f"/api/v1/tasks/{task_id}")
        response.raise_for_status()
        return response.json()

    async def wait_for_completion(self, task_id: str, poll_interval: int = 2) -> Dict[str, Any]:
        """Wait for a task to complete"""
        while True:
            status = await self.get_task_status(task_id)

            if status.get("status") in ["completed", "failed"]:
                return status

            print(f"Task status: {status.get('status')} - Waiting...")
            await asyncio.sleep(poll_interval)


class WebAppIntegration:
    """Example of integrating Webis into a web application"""

    def __init__(self, webis_client: WebisAPIClient):
        self.webis = webis_client

    async def search_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """Search the knowledge base"""
        result = await self.webis.run_pipeline(
            query=query,
            sources=["local_kb"],
            limit=5
        )
        return result.get("results", [])

    async def analyze_document(self, file_path: str) -> Dict[str, Any]:
        """Analyze an uploaded document"""
        result = await self.webis.extract_data(
            file_path=file_path,
            task="Extract key insights and summarize"
        )
        return result

    async def background_task(self, query: str) -> str:
        """Start a background pipeline task"""
        result = await self.webis.run_pipeline(
            query=query,
            sources=["duckduckgo", "gnews"],
            limit=10
        )
        return result.get("task_id")


async def example_flask_integration():
    """Example Flask integration"""

    print("=" * 60)
    print("Flask Integration Example")
    print("=" * 60)

    # Note: This is a conceptual example
    print("\nFlask app structure:")
    print("-" * 60)

    flask_code = '''
from flask import Flask, request, jsonify
from webis_integration import WebisAPIClient

app = Flask(__name__)
webis = WebisAPIClient("http://localhost:8000", "your_api_key")

@app.route("/api/search", methods=["POST"])
async def search():
    query = request.json.get("query")

    # Use Webis to search knowledge base
    results = await webis.run_pipeline(query=query, limit=10)

    return jsonify(results)

@app.route("/api/analyze", methods=["POST"])
async def analyze_document():
    file = request.files['document']

    # Save and analyze document
    file_path = f"/tmp/{file.filename}"
    file.save(file_path)

    result = await webis.extract_data(
        file_path=file_path,
        task="Extract key information"
    )

    return jsonify(result)

if __name__ == "__main__":
    app.run(debug=True)
    '''

    print(flask_code)


async def example_fastapi_integration():
    """Example FastAPI integration"""

    print("\n\n" + "=" * 60)
    print("FastAPI Integration Example")
    print("=" * 60)

    # Note: This is a conceptual example
    print("\nFastAPI app structure:")
    print("-" * 60)

    fastapi_code = '''
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from webis_integration import WebisAPIClient

app = FastAPI()
webis = WebisAPIClient("http://localhost:8000", "your_api_key")

@app.post("/api/search")
async def search(query: str, limit: int = 10):
    """Search knowledge base"""
    try:
        result = await webis.run_pipeline(
            query=query,
            sources=["local_kb"],
            limit=limit
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_document(file: UploadFile):
    """Analyze uploaded document"""
    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        result = await webis.extract_data(
            file_path=file_path,
            task="Extract key insights"
        )
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    """Get task status"""
    try:
        result = await webis.get_task_status(task_id)
        return JSONResponse(content=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    '''

    print(fastapi_code)


async def example_streamlit_integration():
    """Example Streamlit integration"""

    print("\n\n" + "=" * 60)
    print("Streamlit Integration Example")
    print("=" * 60)

    streamlit_code = '''
import streamlit as st
from webis_integration import WebisAPIClient

# Initialize Webis client
webis = WebisAPIClient("http://localhost:8000", st.secrets["WEBIS_API_KEY"])

st.title("Webis-Powered Application")

# Search interface
query = st.text_input("Search knowledge base:", "Enter your query...")

if st.button("Search"):
    with st.spinner("Searching..."):
        results = await webis.run_pipeline(query=query, limit=10)

    st.success(f"Found {len(results.get('results', []))} results")

    for result in results.get('results', []):
        st.markdown(f"### {result.get('title', 'No title')}")
        st.write(result.get('content', 'No content'))

# Document analysis interface
st.header("Document Analysis")
uploaded_file = st.file_uploader("Upload a document", type=['pdf', 'docx'])

if uploaded_file:
    file_path = f"/tmp/{uploaded_file.name}"

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with st.spinner("Analyzing..."):
        result = await webis.extract_data(
            file_path=file_path,
            task="Extract key information and summarize"
        )

    st.json(result)
    '''

    print(streamlit_code)


async def example_cli_integration():
    """Example CLI integration"""

    print("\n\n" + "=" * 60)
    print("CLI Integration Example")
    print("=" * 60)

    # Note: This is a conceptual example
    print("\nCLI tool structure:")
    print("-" * 60)

    cli_code = '''
import click
from webis_integration import WebisAPIClient

@click.group()
def cli():
    """Webis CLI integration"""
    pass

@cli.command()
@click.argument("query")
@click.option("--limit", default=10, help="Number of results")
def search(query: str, limit: int):
    """Search knowledge base"""
    webis = WebisAPIClient("http://localhost:8000", "your_api_key")

    result = asyncio.run(webis.run_pipeline(query=query, limit=limit))

    click.echo(f"Found {len(result.get('results', []))} results")

    for item in result.get('results', []):
        click.echo(f"  - {item.get('title', 'No title')}")

@cli.command()
@click.argument("file_path")
@click.option("--task", help="Analysis task")
def analyze(file_path: str, task: str):
    """Analyze a document"""
    webis = WebisAPIClient("http://localhost:8000", "your_api_key")

    result = asyncio.run(webis.extract_data(
        file_path=file_path,
        task=task or "Extract key information"
    ))

    click.echo(json.dumps(result, indent=2))

if __name__ == "__main__":
    cli()
    '''

    print(cli_code)


async def example_websocket_integration():
    """Example WebSocket integration for real-time updates"""

    print("\n\n" + "=" * 60)
    print("WebSocket Integration Example")
    print("=" * 60)

    websocket_code = '''
import asyncio
import websockets
import json
from webis_integration import WebisAPIClient

async def webis_client_handler(websocket: websockets.WebSocketServerProtocol):
    """Handle WebSocket client connections"""
    webis = WebisAPIClient("http://localhost:8000", "your_api_key")

    try:
        async for message in websocket:
            data = json.loads(message)

            # Handle search requests
            if data.get("action") == "search":
                result = await webis.run_pipeline(
                    query=data["query"],
                    limit=data.get("limit", 10)
                )
                await websocket.send(json.dumps({
                    "type": "search_result",
                    "data": result
                }))

            # Handle document analysis
            elif data.get("action") == "analyze":
                result = await webis.extract_data(
                    file_path=data["file_path"],
                    task=data.get("task", "Extract key information")
                )
                await websocket.send(json.dumps({
                    "type": "analysis_result",
                    "data": result
                }))

            # Handle task status
            elif data.get("action") == "status":
                result = await webis.get_task_status(data["task_id"])
                await websocket.send(json.dumps({
                    "type": "task_status",
                    "data": result
                }))

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    """Start WebSocket server"""
    server = await websockets.serve(webis_client_handler, "localhost", 8765)
    await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
    '''

    print(websocket_code)


async def demonstrate_api_client():
    """Demonstrate the Webis API client"""

    print("\n\n" + "=" * 60)
    print("API Client Demonstration")
    print("=" * 60)

    # Initialize client
    client = WebisAPIClient(
        base_url="http://localhost:8000",
        api_key="your_api_key_here"
    )

    # Example 1: Run pipeline
    print("\n1. Running Pipeline...")
    print("-" * 60)

    result = await client.run_pipeline(
        query="Latest AI developments",
        sources=["duckduckgo"],
        limit=5
    )

    print(f"Task ID: {result.get('task_id')}")
    print(f"Status: {result.get('status')}")

    # Example 2: Wait for completion
    if result.get("task_id"):
        print("\n2. Waiting for completion...")
        print("-" * 60)

        final_result = await client.wait_for_completion(result["task_id"])
        print(f"Final status: {final_result.get('status')}")

    # Example 3: Extract data
    print("\n3. Extracting data from file...")
    print("-" * 60)

    # Note: You need a real file for this to work
    # extract_result = await client.extract_data(
    #     file_path="./sample.pdf",
    #     task="Extract key findings"
    # )
    # print(f"Extraction result: {extract_result}")


if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demonstrate_api_client())
    asyncio.run(example_flask_integration())
    asyncio.run(example_fastapi_integration())
    asyncio.run(example_streamlit_integration())
    asyncio.run(example_cli_integration())
    asyncio.run(example_websocket_integration())

    print("\n\n" + "=" * 60)
    print("API Integration Examples Complete!")
    print("=" * 60)
    print("\nIntegration patterns demonstrated:")
    print("  ✓ Flask web application")
    print("  ✓ FastAPI web application")
    print("  ✓ Streamlit application")
    print("  ✓ CLI tool")
    print("  ✓ WebSocket real-time updates")
    print("\nChoose the pattern that fits your application needs!")