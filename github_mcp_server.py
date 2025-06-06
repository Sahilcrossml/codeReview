# github_mcp_server.py
from mcp import Server
import requests
import os
from typing import Dict, List, Optional
import base64
import json

class GitHubMCPServer:
    def __init__(self):
        self.server = Server("github-operations")
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        self.base_url = "https://api.github.com"
        self.register_tools()
    
    def register_tools(self):
        @self.server.tool("get_pr_details")
        async def get_pr_details(owner: str, repo: str, pr_number: int) -> str:
            """Get PR details from GitHub"""
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"
            return json.dumps(response.json())
        
        @self.server.tool("get_pr_diff")
        async def get_pr_diff(owner: str, repo: str, pr_number: int) -> str:
            """Get PR diff from GitHub"""
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}"
            headers = {**self.headers, "Accept": "application/vnd.github.v3.diff"}
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"
            return response.text
        
        @self.server.tool("get_pr_files")
        async def get_pr_files(owner: str, repo: str, pr_number: int) -> str:
            """Get changed files in PR"""
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/files"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"
            return json.dumps(response.json())
        
        @self.server.tool("get_file_content")
        async def get_file_content(owner: str, repo: str, path: str, ref: str = "main") -> str:
            """Get file content from GitHub"""
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}?ref={ref}"
            response = requests.get(url, headers=self.headers)
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}"
            data = response.json()
            if 'content' in data:
                return base64.b64decode(data['content']).decode('utf-8')
            return "File content not available"
        
        @self.server.tool("create_pr_review")
        async def create_pr_review(owner: str, repo: str, pr_number: int, 
                                 body: str, event: str = "COMMENT") -> str:
            """Create a PR review"""
            url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
            data = {
                "body": body,
                "event": event  # APPROVE, REQUEST_CHANGES, COMMENT
            }
            response = requests.post(url, headers=self.headers, json=data)
            if response.status_code not in [200, 201]:
                return f"Error: {response.status_code} - {response.text}"
            return json.dumps(response.json())

# For running as standalone server
if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server
    
    server = GitHubMCPServer()
    
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                server.server.create_initialization_options()
            )
    
    asyncio.run(main())