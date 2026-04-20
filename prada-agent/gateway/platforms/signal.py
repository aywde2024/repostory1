"""
PRADA Agent - Signal Platform Adapter

Signal messaging platform integration via signal-cli bridge.
"""

import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime

from gateway.platforms.base import PlatformAdapter, PlatformMessage, PlatformConfig


@dataclass
class SignalConfig(PlatformConfig):
    """Signal platform configuration."""
    phone_number: str = ""
    signal_cli_path: str = "/usr/bin/signal-cli"
    config_dir: str = "~/.signal-cli"
    
    @classmethod
    def from_env(cls) -> "SignalConfig":
        import os
        return cls(
            phone_number=os.getenv("SIGNAL_PHONE_NUMBER", ""),
            signal_cli_path=os.getenv("SIGNAL_CLI_PATH", "/usr/bin/signal-cli"),
            config_dir=os.getenv("SIGNAL_CONFIG_DIR", "~/.signal-cli")
        )


class SignalAdapter(PlatformAdapter):
    """Signal messaging platform adapter."""
    
    name = "signal"
    display_name = "Signal"
    
    def __init__(self, config: SignalConfig):
        super().__init__(config)
        self.config = config
        self._connected = False
    
    async def connect(self) -> bool:
        """Connect to Signal via signal-cli."""
        try:
            # Verify signal-cli is available
            proc = await asyncio.create_subprocess_exec(
                self.config.signal_cli_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                self._connected = True
                self.logger.info(f"Connected to Signal: {stdout.decode().strip()}")
                return True
            
            self.logger.error(f"signal-cli not available: {stderr.decode()}")
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Signal: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from Signal."""
        self._connected = False
        self.logger.info("Disconnected from Signal")
    
    async def send_message(
        self,
        recipient: str,
        content: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send a message via Signal."""
        if not self._connected:
            await self.connect()
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self.config.signal_cli_path,
                "-u", self.config.phone_number,
                "send", "-m", content, recipient,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode == 0:
                self.logger.debug(f"Message sent to {recipient}")
                return True
            else:
                self.logger.error(f"Failed to send message: {stderr.decode()}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending Signal message: {e}")
            return False
    
    async def send_image(
        self,
        recipient: str,
        image_path: str,
        caption: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send an image via Signal."""
        if not self._connected:
            await self.connect()
        
        try:
            cmd = [
                self.config.signal_cli_path,
                "-u", self.config.phone_number,
                "send", "-a", image_path, recipient
            ]
            
            if caption:
                cmd.extend(["-m", caption])
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            return proc.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Error sending Signal image: {e}")
            return False
    
    async def send_file(
        self,
        recipient: str,
        file_path: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send a file via Signal (same as image)."""
        return await self.send_image(recipient, file_path)
    
    async def start_listening(self, callback: Callable[[PlatformMessage], None]):
        """Start listening for incoming messages."""
        self.logger.info("Signal listener started (requires external webhook/polling)")
        # Signal CLI doesn't have built-in server mode
        # Would need external polling or dbus integration
    
    def supports_features(self) -> Dict[str, bool]:
        """Return supported platform features."""
        return {
            "voice": False,
            "images": True,
            "files": True,
            "threads": False,
            "reactions": False,
            "typing_indicator": False,
            "streaming": True
        }


def create_adapter() -> SignalAdapter:
    """Factory function to create Signal adapter."""
    config = SignalConfig.from_env()
    return SignalAdapter(config)


if __name__ == "__main__":
    async def test():
        adapter = create_adapter()
        
        print("Testing Signal Adapter...")
        connected = await adapter.connect()
        print(f"Connected: {connected}")
        
        if connected:
            # Test send message
            success = await adapter.send_message(
                "+1234567890",
                "Test message from PRADA Agent"
            )
            print(f"Message sent: {success}")
        
        await adapter.disconnect()
    
    asyncio.run(test())
