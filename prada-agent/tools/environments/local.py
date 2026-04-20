"""
Local Terminal Backend - Direct subprocess execution
"""

import os
import subprocess
import signal
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool = False


class LocalBackend:
    """Execute commands locally using subprocess"""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command locally"""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.working_dir,
                env={**os.environ, **(env or {})},
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
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                timed_out=False
            )
    
    def is_available(self) -> bool:
        """Local backend is always available"""
        return True
    
    def get_working_dir(self) -> str:
        return self.working_dir
