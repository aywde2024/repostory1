"""
Daytona Terminal Backend - Workspace-as-a-service execution
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from .local import ExecutionResult


class DaytonaBackend:
    """Execute commands on Daytona workspaces"""
    
    def __init__(
        self, 
        workspace_id: Optional[str] = None,
        api_key_env: str = "DAYTONA_API_KEY",
        auto_stop_minutes: int = 60,
        region: str = "us-east-1"
    ):
        self.workspace_id = workspace_id or os.environ.get("DAYTONA_WORKSPACE_ID")
        self.api_key_env = api_key_env
        self.auto_stop_minutes = auto_stop_minutes
        self.region = region
        self._session = None
    
    def _get_client(self):
        """Create Daytona API client"""
        try:
            import requests
            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                raise RuntimeError(f"{self.api_key_env} environment variable not set")
            
            self._session = requests.Session()
            self._session.headers.update({
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            })
            return self._session
        except ImportError:
            raise RuntimeError("requests not installed. Run: pip install requests")
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command on Daytona workspace"""
        try:
            session = self._get_client()
            
            if not self.workspace_id:
                return ExecutionResult(
                    stdout="",
                    stderr="DAYTONA_WORKSPACE_ID not set",
                    exit_code=-1,
                    timed_out=False
                )
            
            # Build exec request
            exec_url = f"https://api.daytona.io/v1/workspaces/{self.workspace_id}/exec"
            
            payload = {
                "command": command,
                "workingDir": cwd or "/workspace",
                "env": env or {},
                "timeout": timeout,
            }
            
            response = session.post(exec_url, json=payload, timeout=timeout + 30)
            response.raise_for_status()
            
            result = response.json()
            
            return ExecutionResult(
                stdout=result.get("stdout", ""),
                stderr=result.get("stderr", ""),
                exit_code=result.get("exitCode", -1),
                timed_out=False
            )
            
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                timed_out=False
            )
    
    def is_available(self) -> bool:
        """Check if Daytona backend is available"""
        try:
            import requests
            api_key = os.environ.get(self.api_key_env)
            workspace_id = self.workspace_id or os.environ.get("DAYTONA_WORKSPACE_ID")
            return bool(api_key and workspace_id)
        except ImportError:
            return False
    
    def get_working_dir(self) -> str:
        return "/workspace"
