"""
PRADA Agent - Email Platform Adapter

Email integration via IMAP/SMTP for bidirectional messaging.
"""

import asyncio
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime
import base64

from gateway.platforms.base import PlatformAdapter, PlatformMessage, PlatformConfig


@dataclass
class EmailConfig(PlatformConfig):
    """Email platform configuration."""
    email_address: str = ""
    imap_server: str = ""
    imap_port: int = 993
    smtp_server: str = ""
    smtp_port: int = 587
    password: str = ""
    use_ssl: bool = True
    
    @classmethod
    def from_env(cls) -> "EmailConfig":
        import os
        return cls(
            email_address=os.getenv("EMAIL_ADDRESS", ""),
            imap_server=os.getenv("EMAIL_IMAP_SERVER", ""),
            imap_port=int(os.getenv("EMAIL_IMAP_PORT", "993")),
            smtp_server=os.getenv("EMAIL_SMTP_SERVER", ""),
            smtp_port=int(os.getenv("EMAIL_SMTP_PORT", "587")),
            password=os.getenv("EMAIL_PASSWORD", ""),
            use_ssl=os.getenv("EMAIL_USE_SSL", "true").lower() == "true"
        )


class EmailAdapter(PlatformAdapter):
    """Email messaging platform adapter."""
    
    name = "email"
    display_name = "Email"
    
    def __init__(self, config: EmailConfig):
        super().__init__(config)
        self.config = config
        self._imap_conn: Optional[imaplib.IMAP4_SSL] = None
        self._smtp_conn: Optional[smtplib.SMTP] = None
    
    async def connect(self) -> bool:
        """Connect to email servers."""
        try:
            # Connect to IMAP
            if self.config.use_ssl:
                self._imap_conn = imaplib.IMAP4_SSL(
                    self.config.imap_server,
                    self.config.imap_port
                )
            else:
                self._imap_conn = imaplib.IMAP4(
                    self.config.imap_server,
                    self.config.imap_port
                )
            
            self._imap_conn.login(self.config.email_address, self.config.password)
            self._imap_conn.select("inbox")
            
            # Connect to SMTP
            self._smtp_conn = smtplib.SMTP(
                self.config.smtp_server,
                self.config.smtp_port
            )
            self._smtp_conn.starttls()
            self._smtp_conn.login(self.config.email_address, self.config.password)
            
            self.logger.info(f"Connected to email: {self.config.email_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to email: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from email servers."""
        if self._imap_conn:
            self._imap_conn.close()
            self._imap_conn.logout()
        
        if self._smtp_conn:
            self._smtp_conn.quit()
        
        self.logger.info("Disconnected from email")
    
    async def send_message(
        self,
        recipient: str,
        content: str,
        subject: str = "PRADA Agent",
        thread_id: Optional[str] = None
    ) -> bool:
        """Send an email message."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.email_address
            msg["To"] = recipient
            msg["Subject"] = subject
            
            # Add In-Reply-To header for threading
            if thread_id:
                msg["In-Reply-To"] = thread_id
                msg["References"] = thread_id
            
            msg.attach(MIMEText(content, "plain", "utf-8"))
            
            self._smtp_conn.send_message(msg)
            self.logger.debug(f"Email sent to {recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            return False
    
    async def send_image(
        self,
        recipient: str,
        image_path: str,
        caption: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send an email with image attachment."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.email_address
            msg["To"] = recipient
            msg["Subject"] = caption or "Image from PRADA Agent"
            
            if thread_id:
                msg["In-Reply-To"] = thread_id
            
            if caption:
                msg.attach(MIMEText(caption, "plain", "utf-8"))
            
            # Attach image
            with open(image_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={image_path.split('/')[-1]}"
            )
            msg.attach(part)
            
            self._smtp_conn.send_message(msg)
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email with image: {e}")
            return False
    
    async def send_file(
        self,
        recipient: str,
        file_path: str,
        thread_id: Optional[str] = None
    ) -> bool:
        """Send an email with file attachment."""
        try:
            msg = MIMEMultipart()
            msg["From"] = self.config.email_address
            msg["To"] = recipient
            msg["Subject"] = "File from PRADA Agent"
            
            if thread_id:
                msg["In-Reply-To"] = thread_id
            
            # Attach file
            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={file_path.split('/')[-1]}"
            )
            msg.attach(part)
            
            self._smtp_conn.send_message(msg)
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending email with file: {e}")
            return False
    
    async def fetch_messages(
        self,
        limit: int = 10,
        unread_only: bool = True
    ) -> List[PlatformMessage]:
        """Fetch recent emails."""
        messages = []
        
        try:
            if unread_only:
                status, data = self._imap_conn.search(None, "UNSEEN")
            else:
                status, data = self._imap_conn.search(None, "ALL")
            
            email_ids = data[0].split()[-limit:]
            
            for email_id in reversed(email_ids):
                status, msg_data = self._imap_conn.fetch(email_id, "(RFC822)")
                
                raw_email = msg_data[0][1]
                email_msg = email.message_from_bytes(raw_email)
                
                # Extract content
                content = ""
                if email_msg.is_multipart():
                    for part in email_msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                content = part.get_payload(decode=True).decode("utf-8")
                            except:
                                pass
                            break
                else:
                    content = email_msg.get_payload(decode=True).decode("utf-8")
                
                messages.append(PlatformMessage(
                    id=email_id.decode(),
                    sender=email_msg.get("From", ""),
                    content=content,
                    timestamp=datetime.now(),
                    thread_id=email_msg.get("Message-ID", ""),
                    platform="email"
                ))
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Error fetching emails: {e}")
            return []
    
    async def start_listening(self, callback: Callable[[PlatformMessage], None]):
        """Start polling for new emails."""
        self.logger.info("Email listener started (polling mode)")
        
        while True:
            try:
                new_messages = await self.fetch_messages(limit=5, unread_only=True)
                for msg in new_messages:
                    await callback(msg)
                
                await asyncio.sleep(30)  # Poll every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in email polling: {e}")
                await asyncio.sleep(60)
    
    def supports_features(self) -> Dict[str, bool]:
        """Return supported platform features."""
        return {
            "voice": False,
            "images": True,
            "files": True,
            "threads": True,
            "reactions": False,
            "typing_indicator": False,
            "streaming": False
        }


def create_adapter() -> EmailAdapter:
    """Factory function to create Email adapter."""
    config = EmailConfig.from_env()
    return EmailAdapter(config)


if __name__ == "__main__":
    async def test():
        adapter = create_adapter()
        
        print("Testing Email Adapter...")
        connected = await adapter.connect()
        print(f"Connected: {connected}")
        
        if connected:
            # Test send message
            success = await adapter.send_message(
                "test@example.com",
                "Test message from PRADA Agent",
                subject="PRADA Test"
            )
            print(f"Message sent: {success}")
            
            # Fetch messages
            messages = await adapter.fetch_messages(limit=5)
            print(f"Fetched {len(messages)} messages")
        
        await adapter.disconnect()
    
    asyncio.run(test())
