"""
Modal Terminal Backend - Cloud function execution with persistent volumes
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from .local import ExecutionResult


class ModalBackend:
    """Execute commands on Modal cloud functions"""
    
    def __init__(
        self, 
        image: str = "modal-labs/hermes:latest",
        cpu: int = 2,
        memory: int = 4096,
        gpu: Optional[str] = None,
        volume: str = "hermes-home",
        auto_sleep_minutes: int = 30,
        region: str = "us-east-1"
    ):
        self.image = image
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self.volume = volume
        self.auto_sleep_minutes = auto_sleep_minutes
        self.region = region
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command on Modal cloud"""
        try:
            import modal
            
            # Create or get app
            app = modal.App("prada-agent")
            
            # Define volume
            volume_obj = modal.Volume.from_name(self.volume, create_if_missing=True)
            
            # Build image
            img = modal.Image.from_registry(self.image)
            
            # Define function
            @app.function(
                image=img,
                cpu=self.cpu,
                memory=self.memory,
                gpu=self.gpu,
                volumes={"/root/.prada": volume_obj},
                timeout=timeout,
            )
            def run_command(cmd: str, working_dir: str, env_vars: dict):
                import subprocess
                import os
                
                # Set environment
                for key, value in env_vars.items():
                    os.environ[key] = value
                
                # Run command
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=working_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }
            
            # Execute remotely
            target_dir = cwd or "/root/.prada"
            result = run_command.remote(command, target_dir, env or {})
            
            return ExecutionResult(
                stdout=result["stdout"],
                stderr=result["stderr"],
                exit_code=result["exit_code"],
                timed_out=False
            )
            
        except ImportError:
            return ExecutionResult(
                stdout="",
                stderr="modal not installed. Run: pip install modal",
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
        """Check if Modal backend is available"""
        try:
            import modal
            # Check for credentials
            return bool(os.environ.get("MODAL_TOKEN_ID") and os.environ.get("MODAL_TOKEN_SECRET"))
        except ImportError:
            return False
    
    def get_working_dir(self) -> str:
        return "/root/.prada"
