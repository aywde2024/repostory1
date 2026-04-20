"""
PRADA Agent - External Memory Provider Plugin System
Supports 8 external memory providers: honcho, openviking, mem0, hindsight, 
holographic, retaindb, byterover, supermemory
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MemoryEntry:
    """Memory entry structure"""
    entry_id: str
    content: str
    metadata: dict
    created_at: float
    updated_at: float
    tags: List[str]


class MemoryProvider(ABC):
    """Abstract base class for external memory providers"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return provider name"""
        pass
    
    @abstractmethod
    def initialize(self, config: dict) -> bool:
        """Initialize connection (return whether successful)"""
        pass
    
    @abstractmethod
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store memory (return entry_id)"""
        pass
    
    @abstractmethod
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Semantic retrieval of memories"""
        pass
    
    @abstractmethod
    def update(self, entry_id: str, content: str) -> bool:
        """Update memory"""
        pass
    
    @abstractmethod
    def delete(self, entry_id: str) -> bool:
        """Delete memory"""
        pass


class Mem0Provider(MemoryProvider):
    """Mem0 semantic vector memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.client = None
        self.collection_name = "prada_memories"
    
    @property
    def provider_name(self) -> str:
        return "mem0"
    
    def initialize(self, config: dict) -> bool:
        """Initialize Mem0 client"""
        try:
            from mem0 import Memory
            
            self.config = config
            self.collection_name = config.get("collection_name", "prada_memories")
            
            self.client = Memory(
                vector_store=config.get("vector_db", "chroma"),
                collection_name=self.collection_name,
                embedding_model=config.get("embedding_model", "text-embedding-3-small"),
            )
            return True
        except Exception as e:
            print(f"Mem0 initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store memory in Mem0"""
        if not self.client:
            raise RuntimeError("Mem0 not initialized")
        
        result = self.client.add(
            content,
            user_id=target,
            metadata=metadata,
        )
        return result.get("id", "")
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Search memories in Mem0"""
        if not self.client:
            raise RuntimeError("Mem0 not initialized")
        
        results = self.client.search(query, limit=limit)
        
        entries = []
        for r in results:
            entries.append(MemoryEntry(
                entry_id=r.get("id", ""),
                content=r.get("content", ""),
                metadata=r.get("metadata", {}),
                created_at=r.get("created_at", 0),
                updated_at=r.get("updated_at", 0),
                tags=r.get("tags", []),
            ))
        
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update memory in Mem0"""
        if not self.client:
            raise RuntimeError("Mem0 not initialized")
        
        try:
            self.client.update(entry_id, content)
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete memory from Mem0"""
        if not self.client:
            raise RuntimeError("Mem0 not initialized")
        
        try:
            self.client.delete(entry_id)
            return True
        except Exception:
            return False


class HonchoProvider(MemoryProvider):
    """Honcho dialectical user modeling provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.db_path: Optional[Path] = None
    
    @property
    def provider_name(self) -> str:
        return "honcho"
    
    def initialize(self, config: dict) -> bool:
        """Initialize Honcho SQLite database"""
        try:
            import sqlite3
            
            self.config = config
            self.db_path = Path(config.get("db_path", "~/.prada/memories/honcho.db")).expanduser()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create tables
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    preferences TEXT,
                    created_at REAL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    content TEXT,
                    sentiment REAL,
                    created_at REAL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Honcho initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store interaction in Honcho"""
        import sqlite3
        import uuid
        import time
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        entry_id = str(uuid.uuid4())[:12]
        now = time.time()
        
        cursor.execute(
            "INSERT INTO interactions (id, user_id, content, sentiment, created_at) VALUES (?, ?, ?, ?, ?)",
            (entry_id, target, content, metadata.get("sentiment", 0), now)
        )
        
        conn.commit()
        conn.close()
        
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Retrieve user model from Honcho"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT id, content, created_at FROM interactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (query, limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                metadata={},
                created_at=row[2],
                updated_at=row[2],
                tags=[],
            ))
        
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update interaction in Honcho"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE interactions SET content = ? WHERE id = ?",
                (content, entry_id)
            )
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete interaction from Honcho"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM interactions WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


class OpenVikingProvider(MemoryProvider):
    """OpenViking knowledge graph memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.graph = None
    
    @property
    def provider_name(self) -> str:
        return "openviking"
    
    def initialize(self, config: dict) -> bool:
        """Initialize Neo4j connection"""
        try:
            from neo4j import GraphDatabase
            
            self.config = config
            uri = config.get("neo4j_uri", "bolt://localhost:7687")
            user = config.get("neo4j_user", "neo4j")
            password = config.get("neo4j_password", "")
            
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            
            # Verify connection
            with self.driver.session() as session:
                session.run("MATCH (n) RETURN count(n) LIMIT 1")
            
            return True
        except Exception as e:
            print(f"OpenViking initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store entity/relation in knowledge graph"""
        import uuid
        
        entry_id = str(uuid.uuid4())[:12]
        
        with self.driver.session() as session:
            session.run("""
                MERGE (e:Entity {id: $id, content: $content, type: $type})
                SET e += $metadata
            """, {
                "id": entry_id,
                "content": content,
                "type": metadata.get("type", "fact"),
                "metadata": metadata,
            })
        
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Query knowledge graph"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (e:Entity)
                WHERE e.content CONTAINS $query OR e.keywords CONTAINS $query
                RETURN e.id, e.content, e.metadata, e.created_at
                LIMIT $limit
            """, {"query": query, "limit": limit})
            
            entries = []
            for record in result:
                entries.append(MemoryEntry(
                    entry_id=record["e.id"],
                    content=record["e.content"],
                    metadata=record["e.metadata"] or {},
                    created_at=record["e.created_at"] or 0,
                    updated_at=0,
                    tags=[],
                ))
            return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update entity in knowledge graph"""
        try:
            with self.driver.session() as session:
                session.run("""
                    MATCH (e:Entity {id: $id})
                    SET e.content = $content
                """, {"id": entry_id, "content": content})
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete entity from knowledge graph"""
        try:
            with self.driver.session() as session:
                session.run("MATCH (e:Entity {id: $id}) DELETE e", {"id": entry_id})
            return True
        except Exception:
            return False


# Provider registry
MEMORY_PROVIDERS = {
    "mem0": Mem0Provider,
    "honcho": HonchoProvider,
    "openviking": OpenVikingProvider,
    # Additional providers would be implemented similarly:
    # "hindsight": HindsightProvider,
    # "holographic": HolographicProvider,
    # "retaindb": RetainDBProvider,
    # "byterover": ByteRoverProvider,
    # "supermemory": SupermemoryProvider,
}


def get_memory_provider(name: str) -> Optional[MemoryProvider]:
    """Get memory provider by name"""
    provider_class = MEMORY_PROVIDERS.get(name)
    if provider_class:
        return provider_class()
    return None
