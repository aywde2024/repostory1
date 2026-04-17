"""
Singularity Terminal Backend - HPC/scientific computing container execution
"""

import os
import subprocess
from typing import Dict, Optional
from dataclasses import dataclass

from .local import ExecutionResult


class SingularityBackend:
    """Execute commands in Singularity/Apptainer containers"""
    
    def __init__(
        self, 
        image: str = "/opt/images/hermes.sif",
        bind_paths: Optional[list] = None,
        working_dir: str = "/workspace"
    ):
        self.image = image
        self.bind_paths = bind_paths or []
        self.working_dir = working_dir
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command in Singularity container"""
        try:
            # Build singularity exec command
            singularity_cmd = ["singularity", "exec"]
            
            # Add bind paths
            for bind in self.bind_paths:
                singularity_cmd.extend(["--bind", bind])
            
            # Add environment variables
            if env:
                for key, value in env.items():
                    singularity_cmd.extend(["--env", f"{key}={value}"])
            
            # Add image and command
            singularity_cmd.extend([self.image, "bash", "-c", command])
            
            result = subprocess.run(
                singularity_cmd,
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
                stderr="Singularity/Apptainer not found. Please install singularity or apptainer.",
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
        """Check if Singularity is available"""
        try:
            # Try both singularity and apptainer (renamed)
            for cmd in ["singularity", "apptainer"]:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return True
            return False
        except Exception:
            return False
    
    def get_working_dir(self) -> str:
        return self.working_dir
