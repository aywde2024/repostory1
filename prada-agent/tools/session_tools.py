"""
Session Tools - Session management and search operations
"""

import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


async def session_list_impl(
    limit: int = 10,
    platform: Optional[str] = None,
    days: Optional[int] = None,
) -> dict:
    """List recent sessions."""
    prada_home = Path.home() / ".prada"
    state_file = prada_home / "state.db"
    
    if not state_file.exists():
        return {"success": True, "output": []}
    
    try:
        import aiosqlite
        async with aiosqlite.connect(str(state_file)) as db:
            query = "SELECT session_id, user_id, platform, created_at FROM sessions WHERE 1=1"
            params = []
            
            if platform:
                query += " AND platform = ?"
                params.append(platform)
            
            if days:
                query += " AND created_at >= datetime('now', ?)"
                params.append(f"-{days} days")
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                
            sessions = [
                {
                    "session_id": row[0],
                    "user_id": row[1],
                    "platform": row[2],
                    "created_at": row[3],
                }
                for row in rows
            ]
            
            return {"success": True, "output": sessions}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def session_search_impl(
    query: str,
    limit: int = 5,
    days: Optional[int] = None,
    platform: Optional[str] = None,
) -> dict:
    """Search sessions using full-text search."""
    prada_home = Path.home() / ".prada"
    state_file = prada_home / "state.db"
    
    if not state_file.exists():
        return {"success": True, "output": []}
    
    try:
        import aiosqlite
        async with aiosqlite.connect(str(state_file)) as db:
            # Use FTS5 if available, otherwise fallback to LIKE
            search_query = f"%{query}%"
            
            sql = """
                SELECT s.session_id, s.user_id, s.platform, s.created_at, 
                       m.content as match_content
                FROM sessions s
                LEFT JOIN messages m ON s.session_id = m.session_id
                WHERE (s.user_id LIKE ? OR s.platform LIKE ? OR m.content LIKE ?)
            """
            params = [search_query, search_query, search_query]
            
            if platform:
                sql += " AND s.platform = ?"
                params.append(platform)
            
            if days:
                sql += " AND s.created_at >= datetime('now', ?)"
                params.append(f"-{days} days")
            
            sql += " GROUP BY s.session_id ORDER BY s.created_at DESC LIMIT ?"
            params.append(limit)
            
            async with db.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
            
            results = [
                {
                    "session_id": row[0],
                    "user_id": row[1],
                    "platform": row[2],
                    "created_at": row[3],
                    "snippet": row[4][:200] if row[4] else "",
                }
                for row in rows
            ]
            
            return {"success": True, "output": results}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def session_compress_impl(session_id: str) -> dict:
    """Compress a session to reduce token count."""
    from agent.context_engine import ContextEngine
    from pathlib import Path
    
    prada_home = Path.home() / ".prada"
    engine = ContextEngine(prada_home)
    
    try:
        # Get session messages
        state_file = prada_home / "state.db"
        if not state_file.exists():
            return {"success": False, "error": "No session database found"}
        
        import aiosqlite
        async with aiosqlite.connect(str(state_file)) as db:
            async with db.execute(
                "SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            ) as cursor:
                rows = await cursor.fetchall()
        
        messages = [{"role": r[0], "content": r[1]} for r in rows]
        
        if not messages:
            return {"success": False, "error": f"No messages found for session {session_id}"}
        
        # Compress using context engine
        compressed = await engine.compress_messages(messages, target_tokens=2000)
        
        return {
            "success": True,
            "output": f"Compressed {len(messages)} messages to {len(compressed)} entries",
            "original_count": len(messages),
            "compressed_count": len(compressed),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Register tools
try:
    from tools.registry import registry as _registry
    
    _registry.register(
        name="session_list",
        func=session_list_impl,
        schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "platform": {"type": "string"},
                "days": {"type": "integer"}
            }
        },
        description="List recent sessions",
        toolsets=["session", "core"],
    )
    
    _registry.register(
        name="session_search",
        func=session_search_impl,
        schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 5},
                "days": {"type": "integer"},
                "platform": {"type": "string"}
            },
            "required": ["query"]
        },
        description="Search sessions using full-text search",
        toolsets=["session", "core"],
    )
    
    _registry.register(
        name="session_compress",
        func=session_compress_impl,
        schema={
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to compress"}
            },
            "required": ["session_id"]
        },
        description="Compress a session to reduce token count",
        toolsets=["session", "core"],
    )
except Exception:
    pass
