"""
Docker Terminal Backend - Container sandbox execution
"""

import os
import subprocess
from typing import Dict, Optional
from dataclasses import dataclass

from .local import ExecutionResult


class DockerBackend:
    """Execute commands in Docker container sandbox"""
    
    def __init__(
        self, 
        image: str = "hermes-agent:latest",
        volumes: Optional[list] = None,
        working_dir: str = "/workspace"
    ):
        self.image = image
        self.volumes = volumes or []
        self.working_dir = working_dir
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command in Docker container"""
        try:
            # Build docker run command
            docker_cmd = ["docker", "run", "--rm"]
            
            # Add volume mounts
            for vol in self.volumes:
                docker_cmd.extend(["-v", vol])
            
            # Add environment variables
            if env:
                for key, value in env.items():
                    docker_cmd.extend(["-e", f"{key}={value}"])
            
            # Add image and command
            docker_cmd.extend([self.image, "bash", "-c", command])
            
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                timed_out=False
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                stdout="",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                timed_out=True
            )
        except FileNotFoundError:
            return ExecutionResult(
                stdout="",
                stderr="Docker not found. Please install Docker.",
                exit_code=-1,
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
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_working_dir(self) -> str:
        return self.working_dir
