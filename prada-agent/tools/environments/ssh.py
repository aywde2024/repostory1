"""
SSH Terminal Backend - Remote execution via paramiko
"""

import os
from typing import Dict, Optional
from dataclasses import dataclass

from .local import ExecutionResult


class SSHBackend:
    """Execute commands on remote server via SSH"""
    
    def __init__(
        self, 
        host: str,
        user: str,
        port: int = 22,
        key_path: Optional[str] = None,
        password: Optional[str] = None,
        working_dir: str = "~"
    ):
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.password = password
        self.working_dir = working_dir
    
    def _get_client(self):
        """Create SSH client connection"""
        try:
            import paramiko
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_path:
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                    key_filename=self.key_path,
                )
            elif self.password:
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                )
            else:
                # Try agent forwarding
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                )
            return client
        except ImportError:
            raise RuntimeError("paramiko not installed. Run: pip install paramiko")
    
    def execute(
        self, 
        command: str, 
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ) -> ExecutionResult:
        """Execute shell command via SSH"""
        client = None
        try:
            client = self._get_client()
            
            # Build environment setup
            env_setup = ""
            if env:
                for key, value in env.items():
                    env_setup += f"export {key}='{value}'; "
            
            # Change directory and run command
            target_dir = cwd or self.working_dir
            full_command = f"{env_setup}cd {target_dir} && {command}"
            
            stdin, stdout, stderr = client.exec_command(full_command, timeout=timeout)
            
            return ExecutionResult(
                stdout=stdout.read().decode('utf-8', errors='replace'),
                stderr=stderr.read().decode('utf-8', errors='replace'),
                exit_code=stdout.channel.recv_exit_status(),
                timed_out=False
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                timed_out=False
            )
        finally:
            if client:
                client.close()
    
    def is_available(self) -> bool:
        """Check if SSH backend is available"""
        try:
            import paramiko
            return True
        except ImportError:
            return False
    
    def get_working_dir(self) -> str:
        return self.working_dir
