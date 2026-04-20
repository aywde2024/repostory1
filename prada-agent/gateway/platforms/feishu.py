"""
PRADA Agent - Feishu (飞书/企微) 平台适配器

支持功能:
- 文本消息收发
- 图片/文件发送与接收
- 富文本卡片消息
- 线程回复 (Message Thread)
- 表情反应 (Emoji Reaction)
- 输入中状态指示
- 流式响应更新
- 企业机器人认证
- 事件订阅验证

API 文档: https://open.feishu.cn/document
"""

import hashlib
import hmac
import base64
import time
from typing import Optional, Dict, Any, List, AsyncGenerator, Callable
from pathlib import Path
from dataclasses import dataclass
import httpx

from gateway.run import PlatformAdapter, Message, SessionState


class User:
    """User information"""
    def __init__(self, id: str, name: str, display_name: str = None, avatar_url: str = None, is_bot: bool = False):
        self.id = id
        self.name = name
        self.display_name = display_name or name
        self.avatar_url = avatar_url
        self.is_bot = is_bot


@dataclass
class Attachment:
    """Attachment information"""
    type: str
    url: str
    filename: Optional[str] = None
    size: Optional[int] = None
    mime_type: Optional[str] = None


class FeishuAdapter(PlatformAdapter):
    """Feishu (飞书) 平台适配器"""
    
    PLATFORM_NAME = "feishu"
    DISPLAY_NAME = "Feishu (飞书)"
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.app_id = config.get("app_id")
        self.app_secret = config.get("app_secret")
        self.verification_token = config.get("verification_token")
        self.encrypt_key = config.get("encrypt_key")
        self.base_url = "https://open.feishu.cn/open-apis"
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._callback: Optional[Callable[[Message], None]] = None
        
    @property
    def platform_name(self) -> str:
        return self.PLATFORM_NAME
        
    async def _get_access_token(self) -> str:
        """获取访问令牌 (自动刷新)"""
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu token error: {data.get('msg')}")
                
            self._access_token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data["expire"] - 60
            return self._access_token
    
    def _verify_signature(self, timestamp: str, nonce: str, signature: str, body: str) -> bool:
        """验证飞书事件签名"""
        if not self.verification_token:
            return True
            
        calculate_sign = hashlib.sha256(
            (timestamp + nonce + self.verification_token + body).encode()
        ).hexdigest()
        return hmac.compare_digest(signature, calculate_sign)
    
    async def send_message(
        self,
        chat_id: str,
        content: str,
        thread_id: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """发送消息到飞书"""
        token = await self._get_access_token()
        
        # 构建消息体
        msg_type = "text"
        message_content = {"text": content}
        
        # 检测是否为富文本或卡片
        if content.startswith("<"):
            msg_type = "post"
            message_content = {"post": {"zh_cn": {"content": [[{"tag": "text", "text": content}]]}}}
        
        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": message_content
        }
        
        # 线程回复
        if thread_id:
            payload["thread_id"] = thread_id
        if reply_to_message_id:
            payload["reply_id"] = reply_to_message_id
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu send error: {data.get('msg')}")
                
            return data["data"]["message_id"]
    
    async def send_file(
        self,
        chat_id: str,
        file_path: str,
        filename: Optional[str] = None,
        caption: Optional[str] = None,
        **kwargs
    ) -> str:
        """发送文件到飞书"""
        token = await self._get_access_token()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # 1. 上传文件
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {"file": (filename or file_path.name, f)}
                response = await client.post(
                    f"{self.base_url}/im/v1/images",
                    headers={"Authorization": f"Bearer {token}"},
                    files=files,
                    timeout=30
                )
                response.raise_for_status()
                upload_data = response.json()
                
                if upload_data.get("code") != 0:
                    raise Exception(f"Feishu upload error: {upload_data.get('msg')}")
                    
                image_key = upload_data["data"]["image_key"]
                
            # 2. 发送消息引用文件
            msg_type = "file" if file_path.suffix.lower() in [".pdf", ".doc", ".docx", ".xls", ".xlsx"] else "image"
            content = {msg_type: image_key}
            
            if caption:
                content["text"] = caption
                
            response = await client.post(
                f"{self.base_url}/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "receive_id": chat_id,
                    "msg_type": msg_type,
                    "content": content
                },
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu send error: {data.get('msg')}")
                
            return data["data"]["message_id"]
    
    async def send_image(
        self,
        chat_id: str,
        image_path: str,
        caption: Optional[str] = None,
        **kwargs
    ) -> str:
        """发送图片到飞书"""
        return await self.send_file(chat_id, image_path, caption=caption)
    
    async def set_typing(self, chat_id: str, is_typing: bool = True) -> None:
        """设置输入中状态"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/im/v1/chats/{chat_id}/typing",
                headers={"Authorization": f"Bearer {token}"},
                json={"status": 1 if is_typing else 0},
                timeout=5
            )
    
    async def add_reaction(self, message_id: str, emoji: str) -> None:
        """添加表情反应"""
        token = await self._get_access_token()
        
        # 飞书表情映射
        emoji_map = {
            "👍": "PRAY",
            "❤️": "HEART",
            "😄": "LAUGH",
            "😮": "SURPRISE",
            "😢": "SAD",
            "😡": "ANGER"
        }
        
        feishu_emoji = emoji_map.get(emoji, "PRAY")
        
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/im/v1/messages/{message_id}/reactions",
                headers={"Authorization": f"Bearer {token}"},
                json={"emoji_type": feishu_emoji},
                timeout=5
            )
    
    async def edit_message(self, message_id: str, new_content: str) -> None:
        """编辑消息 (飞书仅支持卡片消息编辑)"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            await client.put(
                f"{self.base_url}/im/v1/messages/{message_id}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={
                    "content": {"text": new_content}
                },
                timeout=10
            )
    
    async def delete_message(self, message_id: str) -> None:
        """删除消息"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            await client.delete(
                f"{self.base_url}/im/v1/messages/{message_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
    
    async def get_chat_info(self, chat_id: str) -> Dict[str, Any]:
        """获取聊天信息"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/im/v1/chats/{chat_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu chat info error: {data.get('msg')}")
                
            return {
                "chat_id": chat_id,
                "name": data["data"].get("name", "Unknown"),
                "type": data["data"].get("chat_mode", "unknown"),
                "owner_id": data["data"].get("owner_id")
            }
    
    async def get_user_info(self, user_id: str) -> User:
        """获取用户信息"""
        token = await self._get_access_token()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/contact/v3/users/{user_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu user info error: {data.get('msg')}")
                
            user_data = data["data"]
            return User(
                id=user_id,
                name=user_data.get("name", "Unknown"),
                display_name=user_data.get("name", "Unknown"),
                avatar_url=user_data.get("avatar", {}).get("avatar_72"),
                is_bot=False
            )
    
    async def handle_event(self, event: Dict[str, Any]) -> Optional[Message]:
        """处理飞书事件"""
        header = event.get("header", {})
        event_type = header.get("event_type")
        
        # URL 验证事件
        if event_type == "url_verification":
            return None
            
        # 消息接收事件
        if event_type == "im.message.receive_v1":
            message_data = event.get("event", {}).get("message", {})
            sender_data = event.get("event", {}).get("sender", {})
            
            message_id = message_data.get("message_id")
            chat_id = message_data.get("chat_id")
            content_raw = message_data.get("content", "{}")
            
            # 解析消息内容
            try:
                import json
                content_obj = json.loads(content_raw)
                content = content_obj.get("text", "")
            except:
                content = content_raw
                
            sender_id = sender_data.get("sender_id", {}).get("open_id")
            sender_name = sender_data.get("sender_name", "Unknown")
            
            # 忽略机器人自己的消息
            if sender_data.get("sender_type") == "assistant":
                return None
                
            return Message(
                id=message_id,
                chat_id=chat_id,
                user_id=sender_id,
                user_name=sender_name,
                content=content,
                timestamp=float(message_data.get("create_time", 0)) / 1000,
                platform=self.PLATFORM_NAME,
                is_group=message_data.get("chat_type") == "group",
                thread_id=message_data.get("parent_id"),
                raw=event
            )
            
        return None
    
    async def stream_response(
        self,
        chat_id: str,
        message_id: str,
        content_generator: AsyncGenerator[str, None]
    ) -> str:
        """流式响应 (通过连续编辑实现)"""
        full_content = ""
        last_update_time = time.time()
        
        async for chunk in content_generator:
            full_content += chunk
            
            # 限流：每 0.5 秒更新一次
            if time.time() - last_update_time >= 0.5:
                try:
                    await self.edit_message(message_id, full_content)
                    last_update_time = time.time()
                except:
                    pass  # 忽略编辑失败
                    
        # 最终更新
        await self.edit_message(message_id, full_content)
        return full_content
    
    def is_available(self) -> bool:
        """检查适配器是否可用"""
        return bool(self.app_id and self.app_secret)
    
    def get_required_config(self) -> List[str]:
        """返回必需的配置项"""
        return ["app_id", "app_secret", "verification_token"]
    
    async def start(self, callback: Callable[[Message], None]) -> None:
        """Start listening for messages (webhook mode - external webhook handler calls handle_event)"""
        self._callback = callback
        # Feishu uses webhook mode - events are received via HTTP endpoint
        # The actual webhook server should be started externally
        print(f"Feishu adapter started for {self.platform_name}")
    
    async def stop(self) -> None:
        """Stop listening"""
        self._callback = None
        print(f"Feishu adapter stopped")
    
    async def send_typing(self, chat_id: str, thread_id: Optional[str] = None) -> None:
        """Show typing indicator"""
        await self.set_typing(chat_id, True)
    
    async def send_message(self, chat_id: str, content: str, 
                          thread_id: Optional[str] = None,
                          reply_to: Optional[str] = None,
                          attachments: Optional[List[dict]] = None) -> bool:
        """Send a message to the platform"""
        try:
            await self.send_message_impl(chat_id, content, thread_id, reply_to)
            return True
        except Exception as e:
            print(f"Feishu send_message error: {e}")
            return False
    
    async def send_message_impl(
        self,
        chat_id: str,
        content: str,
        thread_id: Optional[str] = None,
        reply_to_message_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """Internal send message implementation"""
        token = await self._get_access_token()
        
        # 构建消息体
        msg_type = "text"
        message_content = {"text": content}
        
        # 检测是否为富文本或卡片
        if content.startswith("<"):
            msg_type = "post"
            message_content = {"post": {"zh_cn": {"content": [[{"tag": "text", "text": content}]]}}}
        
        payload = {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": message_content
        }
        
        # 线程回复
        if thread_id:
            payload["thread_id"] = thread_id
        if reply_to_message_id:
            payload["reply_id"] = reply_to_message_id
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") != 0:
                raise Exception(f"Feishu send error: {data.get('msg')}")
                
            return data["data"]["message_id"]
