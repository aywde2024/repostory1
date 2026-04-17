"""
PRADA Agent - Terminal Tool Implementation
Supports 6 backends: Local, Docker, SSH, Modal, Daytona, Singularity
"""

import os
import subprocess
import shlex
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from abc import ABC, abstractmethod
import time
import signal

from .registry import registry


@dataclass
class ExecutionResult:
    """Terminal execution result"""
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    command: str
    working_dir: str


class TerminalBackend(ABC):
    """Abstract base class for terminal backends"""
    
    @abstractmethod
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        """Execute shell command, return stdout/stderr/exit_code"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if backend is available (deps/permissions/network)"""
        pass
    
    @abstractmethod
    def get_working_dir(self) -> str:
        """Return working directory for file tool path resolution"""
        pass


class LocalBackend(TerminalBackend):
    """Local subprocess execution (default)"""
    
    def __init__(self, working_dir: Optional[str] = None):
        self.working_dir = working_dir or os.getcwd()
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        # Merge environment
        full_env = os.environ.copy()
        full_env.update(env)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=cwd or self.working_dir,
                env=full_env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd or self.working_dir,
            )
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=f"Command timed out after {timeout}s",
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd or self.working_dir,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd or self.working_dir,
            )
    
    def is_available(self) -> bool:
        return True
    
    def get_working_dir(self) -> str:
        return self.working_dir


class DockerBackend(TerminalBackend):
    """Docker container execution with volume mounting"""
    
    def __init__(self, image: str = "hermes-agent:latest", volumes: Optional[List[str]] = None):
        self.image = image
        self.volumes = volumes or []
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        # Build docker run command
        cmd_parts = ["docker", "run", "--rm"]
        
        # Add volume mounts
        for vol in self.volumes:
            cmd_parts.extend(["-v", vol])
        
        # Add environment variables
        for key, value in env.items():
            cmd_parts.extend(["-e", f"{key}={value}"])
        
        # Add working directory
        cmd_parts.extend(["-w", cwd])
        
        # Add image and command
        cmd_parts.extend([self.image, "bash", "-c", command])
        
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except subprocess.TimeoutExpired as e:
            return ExecutionResult(
                stdout=e.stdout.decode() if e.stdout else "",
                stderr=f"Docker command timed out after {timeout}s",
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
    
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_working_dir(self) -> str:
        return "/workspace"


class SSHBackend(TerminalBackend):
    """SSH remote execution using paramiko"""
    
    def __init__(self, host: str, user: str, port: int = 22, 
                 key_path: Optional[str] = None, password: Optional[str] = None):
        self.host = host
        self.user = user
        self.port = port
        self.key_path = key_path
        self.password = password
        self._client = None
    
    def _get_client(self):
        """Lazy connection"""
        if self._client is None:
            try:
                import paramiko
                self._client = paramiko.SSHClient()
                self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                
                if self.key_path:
                    self._client.connect(
                        self.host,
                        port=self.port,
                        username=self.user,
                        key_filename=self.key_path,
                    )
                else:
                    self._client.connect(
                        self.host,
                        port=self.port,
                        username=self.user,
                        password=self.password,
                    )
            except ImportError:
                raise RuntimeError("paramiko not installed. Install with: pip install paramiko")
        return self._client
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        try:
            client = self._get_client()
            
            # Set environment and change directory
            env_str = " ".join(f"{k}={shlex.quote(v)}" for k, v in env.items())
            full_command = f"{env_str} cd {cwd} && {command}"
            
            stdin, stdout, stderr = client.exec_command(full_command, timeout=timeout)
            
            return ExecutionResult(
                stdout=stdout.read().decode(),
                stderr=stderr.read().decode(),
                exit_code=stdout.channel.recv_exit_status(),
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
    
    def is_available(self) -> bool:
        try:
            import paramiko
            return bool(self.host and self.user)
        except ImportError:
            return False
    
    def get_working_dir(self) -> str:
        return f"/home/{self.user}"


class ModalBackend(TerminalBackend):
    """Modal cloud function execution"""
    
    def __init__(self, image: str = "modal-labs/hermes:latest", 
                 cpu: int = 2, memory: int = 4096, gpu: Optional[str] = None):
        self.image = image
        self.cpu = cpu
        self.memory = memory
        self.gpu = gpu
        self._app = None
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        try:
            import modal
            
            # Create or get app
            app = modal.App.lookup("prada-agent", create_if_missing=True)
            
            # Define remote function
            @app.function(
                image=modal.Image.from_dockerhub(self.image),
                cpu=self.cpu,
                memory=self.memory,
                gpu=self.gpu,
                timeout=timeout,
            )
            def run_command(cmd: str, working_dir: str, env_vars: dict):
                import subprocess
                import os
                
                os.chdir(working_dir)
                full_env = os.environ.copy()
                full_env.update(env_vars)
                
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    env=full_env,
                )
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode,
                }
            
            # Run remotely
            result_data = run_command.remote(command, cwd, env)
            
            return ExecutionResult(
                stdout=result_data["stdout"],
                stderr=result_data["stderr"],
                exit_code=result_data["exit_code"],
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except ImportError:
            return ExecutionResult(
                stdout="",
                stderr="Modal not installed. Install with: pip install modal",
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
    
    def is_available(self) -> bool:
        try:
            import modal
            return os.environ.get("MODAL_TOKEN_ID") is not None
        except ImportError:
            return False
    
    def get_working_dir(self) -> str:
        return "/root"


class DaytonaBackend(TerminalBackend):
    """Daytona workspace execution"""
    
    def __init__(self, workspace_id: str, api_key: str):
        self.workspace_id = workspace_id
        self.api_key = api_key
        self._session = None
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        try:
            import requests
            
            url = f"https://app.daytona.io/api/workspaces/{self.workspace_id}/exec"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "command": command,
                "dir": cwd,
                "env": env,
                "timeout": timeout,
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=timeout + 30)
            response.raise_for_status()
            data = response.json()
            
            return ExecutionResult(
                stdout=data.get("stdout", ""),
                stderr=data.get("stderr", ""),
                exit_code=data.get("exitCode", 0),
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except ImportError:
            return ExecutionResult(
                stdout="",
                stderr="requests not installed",
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
    
    def is_available(self) -> bool:
        return bool(self.workspace_id and self.api_key)
    
    def get_working_dir(self) -> str:
        return "/home/daytona/workspace"


class SingularityBackend(TerminalBackend):
    """Singularity/Apptainer container execution"""
    
    def __init__(self, image: str, bind_paths: Optional[List[str]] = None):
        self.image = image
        self.bind_paths = bind_paths or []
    
    def execute(self, command: str, cwd: str, env: dict, timeout: int) -> ExecutionResult:
        start_time = time.time()
        
        # Build singularity exec command
        cmd_parts = ["singularity", "exec"]
        
        # Add bind paths
        for bind in self.bind_paths:
            cmd_parts.extend(["-B", bind])
        
        # Add environment variables
        for key, value in env.items():
            cmd_parts.extend(["--env", f"{key}={value}"])
        
        # Add image and command
        cmd_parts.extend([self.image, "bash", "-c", f"cd {cwd} && {command}"])
        
        try:
            result = subprocess.run(
                cmd_parts,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return ExecutionResult(
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
        except Exception as e:
            return ExecutionResult(
                stdout="",
                stderr=str(e),
                exit_code=-1,
                duration=time.time() - start_time,
                command=command,
                working_dir=cwd,
            )
    
    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["singularity", "--version"],
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_working_dir(self) -> str:
        return "/home"


# Global backend registry
BACKENDS = {
    "local": LocalBackend,
    "docker": DockerBackend,
    "ssh": SSHBackend,
    "modal": ModalBackend,
    "daytona": DaytonaBackend,
    "singularity": SingularityBackend,
}


def get_backend(backend_type: str, config: dict) -> TerminalBackend:
    """Get terminal backend by type"""
    backend_class = BACKENDS.get(backend_type, LocalBackend)
    return backend_class(**config)


# Terminal tool implementation
TERMINAL_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "Shell command to execute"},
        "cwd": {"type": "string", "description": "Working directory (optional)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default: 60)"},
    },
    "required": ["command"],
}


def terminal_impl(command: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
    """Execute a terminal command"""
    from prada_cli.config import get_config
    
    config = get_config()
    terminal_config = config.get("terminal", {})
    backend_type = terminal_config.get("backend", "local")
    backend_config = terminal_config.get(backend_type, {})
    
    backend = get_backend(backend_type, backend_config)
    
    if not backend.is_available():
        return f"Error: {backend_type} backend is not available"
    
    working_dir = cwd or terminal_config.get("working_dir", backend.get_working_dir())
    env = terminal_config.get("env_passthrough", {})
    
    result = backend.execute(command, working_dir, env, timeout)
    
    output = []
    if result.stdout:
        output.append(f"STDOUT:\n{result.stdout}")
    if result.stderr:
        output.append(f"STDERR:\n{result.stderr}")
    output.append(f"Exit code: {result.exit_code}")
    output.append(f"Duration: {result.duration:.2f}s")
    
    return "\n".join(output)


# Process management tools
PROCESS_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "user": {"type": "string", "description": "Filter by user (optional)"},
    },
}


def process_list_impl(user: Optional[str] = None) -> str:
    """List running processes"""
    cmd = "ps aux"
    if user:
        cmd += f" | grep {user}"
    
    result = terminal_impl(cmd, timeout=10)
    return result


PROCESS_KILL_SCHEMA = {
    "type": "object",
    "properties": {
        "pid": {"type": "integer", "description": "Process ID to kill"},
        "signal": {"type": "string", "description": "Signal to send (default: TERM)"},
    },
    "required": ["pid"],
}


def process_kill_impl(pid: int, signal: str = "TERM") -> str:
    """Kill a process by PID"""
    cmd = f"kill -{signal} {pid}"
    result = terminal_impl(cmd, timeout=10)
    return result


PROCESS_WAIT_SCHEMA = {
    "type": "object",
    "properties": {
        "pid": {"type": "integer", "description": "Process ID to wait for"},
        "timeout": {"type": "integer", "description": "Max wait time in seconds"},
    },
    "required": ["pid"],
}


def process_wait_impl(pid: int, timeout: int = 60) -> str:
    """Wait for a process to complete"""
    import time
    
    start = time.time()
    while time.time() - start < timeout:
        result = terminal_impl(f"ps -p {pid}", timeout=5)
        if str(pid) not in result:
            return f"Process {pid} has completed"
        time.sleep(1)
    
    return f"Timeout waiting for process {pid}"


# Register all terminal tools
registry.register(
    name="terminal",
    func=terminal_impl,
    schema=TERMINAL_SCHEMA,
    toolsets=["terminal", "core"],
    platforms=["linux", "macos", "windows"],
    dangerous=True,
)

registry.register(
    name="process_list",
    func=process_list_impl,
    schema=PROCESS_LIST_SCHEMA,
    toolsets=["terminal"],
    platforms=["linux", "macos", "windows"],
)

registry.register(
    name="process_kill",
    func=process_kill_impl,
    schema=PROCESS_KILL_SCHEMA,
    toolsets=["terminal"],
    platforms=["linux", "macos", "windows"],
    dangerous=True,
)

registry.register(
    name="process_wait",
    func=process_wait_impl,
    schema=PROCESS_WAIT_SCHEMA,
    toolsets=["terminal"],
    platforms=["linux", "macos", "windows"],
)
