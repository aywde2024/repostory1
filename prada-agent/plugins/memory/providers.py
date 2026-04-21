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


class HindsightProvider(MemoryProvider):
    """Hindsight event timeline memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.db_path: Optional[Path] = None
    
    @property
    def provider_name(self) -> str:
        return "hindsight"
    
    def initialize(self, config: dict) -> bool:
        """Initialize time-series database (SQLite-based)"""
        try:
            import sqlite3
            
            self.config = config
            self.db_path = Path(config.get("db_path", "~/.prada/memories/hindsight.db")).expanduser()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    timestamp REAL,
                    event_type TEXT,
                    content TEXT,
                    context TEXT,
                    user_id TEXT
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS timelines (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    event_ids TEXT,
                    user_id TEXT
                )
            """)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Hindsight initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store event in timeline"""
        import sqlite3
        import uuid
        import time
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        entry_id = str(uuid.uuid4())[:12]
        now = time.time()
        
        cursor.execute(
            "INSERT INTO events (id, timestamp, event_type, content, context, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, now, metadata.get("event_type", "general"), content, 
             metadata.get("context", ""), target)
        )
        
        conn.commit()
        conn.close()
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Retrieve events by time range or keyword"""
        import sqlite3
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Query by user_id (target) and search content
        cursor.execute(
            """SELECT id, content, timestamp, event_type FROM events 
               WHERE user_id = ? AND content LIKE ? 
               ORDER BY timestamp DESC LIMIT ?""",
            (query, f"%{query}%", limit)
        )
        
        rows = cursor.fetchall()
        conn.close()
        
        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                metadata={"event_type": row[3]},
                created_at=row[2],
                updated_at=row[2],
                tags=[],
            ))
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update event in timeline"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("UPDATE events SET content = ? WHERE id = ?", (content, entry_id))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete event from timeline"""
        import sqlite3
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM events WHERE id = ?", (entry_id,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False


class HolographicProvider(MemoryProvider):
    """Holographic multimodal vector memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.client = None
    
    @property
    def provider_name(self) -> str:
        return "holographic"
    
    def initialize(self, config: dict) -> bool:
        """Initialize Weaviate/Milvus multimodal vector DB"""
        try:
            import weaviate
            
            self.config = config
            url = config.get("weaviate_url", "http://localhost:8080")
            
            self.client = weaviate.Client(url)
            
            # Create collection if not exists
            if not self.client.schema.exists("MultimodalMemory"):
                self.client.schema.create_class({
                    "class": "MultimodalMemory",
                    "properties": [
                        {"name": "content", "dataType": ["text"]},
                        {"name": "media_type", "dataType": ["text"]},
                        {"name": "user_id", "dataType": ["text"]},
                    ]
                })
            
            return True
        except Exception as e:
            print(f"Holographic initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store multimodal memory"""
        import uuid
        
        entry_id = str(uuid.uuid4())[:12]
        
        obj = {
            "content": content,
            "media_type": metadata.get("media_type", "text"),
            "user_id": target,
        }
        
        self.client.data_object.create(obj, "MultimodalMemory", uuid=entry_id)
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Search multimodal memories"""
        result = self.client.query.get(
            "MultimodalMemory",
            ["content", "media_type", "user_id"]
        ).with_near_text({"concepts": [query]}).with_limit(limit).do()
        
        entries = []
        for item in result.get("data", {}).get("Get", {}).get("MultimodalMemory", []):
            entries.append(MemoryEntry(
                entry_id=item.get("_additional", {}).get("id", ""),
                content=item.get("content", ""),
                metadata={"media_type": item.get("media_type", "text")},
                created_at=0,
                updated_at=0,
                tags=[],
            ))
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update multimodal memory"""
        try:
            self.client.data_object.update(
                {"content": content},
                "MultimodalMemory",
                uuid=entry_id
            )
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete multimodal memory"""
        try:
            self.client.data_object.delete("MultimodalMemory", uuid=entry_id)
            return True
        except Exception:
            return False


class RetainDBProvider(MemoryProvider):
    """RetainDB relational SQL memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.engine = None
    
    @property
    def provider_name(self) -> str:
        return "retaindb"
    
    def initialize(self, config: dict) -> bool:
        """Initialize PostgreSQL/MySQL connection"""
        try:
            from sqlalchemy import create_engine, Column, String, Float, Text
            from sqlalchemy.orm import declarative_base, sessionmaker
            
            self.config = config
            conn_string = config.get("connection_string", "sqlite:///./retaindb.db")
            
            self.engine = create_engine(conn_string)
            Base = declarative_base()
            
            class Memory(Base):
                __tablename__ = 'memories'
                id = Column(String, primary_key=True)
                user_id = Column(String, index=True)
                content = Column(Text)
                category = Column(String)
                importance = Column(Float)
                created_at = Column(Float)
            
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            
            return True
        except Exception as e:
            print(f"RetainDB initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store relational memory"""
        import uuid
        import time
        
        entry_id = str(uuid.uuid4())[:12]
        
        from sqlalchemy import Column, String, Float, Text
        
        memory = {
            'id': entry_id,
            'user_id': target,
            'content': content,
            'category': metadata.get('category', 'general'),
            'importance': metadata.get('importance', 0.5),
            'created_at': time.time()
        }
        
        self.session.execute(
            "INSERT INTO memories (id, user_id, content, category, importance, created_at) VALUES (:id, :user_id, :content, :category, :importance, :created_at)",
            memory
        )
        self.session.commit()
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """SQL query memories"""
        result = self.session.execute(
            "SELECT id, content, category, importance, created_at FROM memories WHERE user_id = :user_id AND content LIKE :query ORDER BY created_at DESC LIMIT :limit",
            {"user_id": query, "query": f"%{query}%", "limit": limit}
        ).fetchall()
        
        entries = []
        for row in result:
            entries.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                metadata={"category": row[2], "importance": row[3]},
                created_at=row[4],
                updated_at=row[4],
                tags=[],
            ))
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update relational memory"""
        try:
            self.session.execute(
                "UPDATE memories SET content = :content WHERE id = :id",
                {"content": content, "id": entry_id}
            )
            self.session.commit()
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete relational memory"""
        try:
            self.session.execute("DELETE FROM memories WHERE id = :id", {"id": entry_id})
            self.session.commit()
            return True
        except Exception:
            return False


class ByteRoverProvider(MemoryProvider):
    """ByteRover binary/code index memory provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.index_path: Optional[Path] = None
    
    @property
    def provider_name(self) -> str:
        return "byterover"
    
    def initialize(self, config: dict) -> bool:
        """Initialize Git-like object store"""
        try:
            import hashlib
            import json
            
            self.config = config
            self.index_path = Path(config.get("index_path", "~/.prada/memories/byterover")).expanduser()
            self.index_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize index file
            index_file = self.index_path / "index.json"
            if not index_file.exists():
                index_file.write_text(json.dumps({"objects": {}}))
            
            return True
        except Exception as e:
            print(f"ByteRover initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store code/file blob"""
        import hashlib
        import json
        
        # Generate hash-based ID
        entry_id = hashlib.sha256(content.encode()).hexdigest()[:12]
        
        # Store object
        obj_path = self.index_path / "objects" / entry_id
        obj_path.parent.mkdir(parents=True, exist_ok=True)
        obj_path.write_text(content)
        
        # Update index
        index_file = self.index_path / "index.json"
        index = json.loads(index_file.read_text())
        index["objects"][entry_id] = {
            "user_id": target,
            "file_path": metadata.get("file_path", ""),
            "language": metadata.get("language", ""),
            "created_at": metadata.get("created_at", 0),
        }
        index_file.write_text(json.dumps(index))
        
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Search code index"""
        import json
        
        index_file = self.index_path / "index.json"
        index = json.loads(index_file.read_text())
        
        entries = []
        for entry_id, meta in list(index["objects"].items())[:limit]:
            if meta.get("user_id") == query:
                obj_path = self.index_path / "objects" / entry_id
                content = obj_path.read_text() if obj_path.exists() else ""
                entries.append(MemoryEntry(
                    entry_id=entry_id,
                    content=content,
                    metadata=meta,
                    created_at=meta.get("created_at", 0),
                    updated_at=0,
                    tags=[],
                ))
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update code blob"""
        try:
            obj_path = self.index_path / "objects" / entry_id
            obj_path.write_text(content)
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete code blob"""
        try:
            import json
            
            obj_path = self.index_path / "objects" / entry_id
            if obj_path.exists():
                obj_path.unlink()
            
            # Remove from index
            index_file = self.index_path / "index.json"
            index = json.loads(index_file.read_text())
            index["objects"].pop(entry_id, None)
            index_file.write_text(json.dumps(index))
            
            return True
        except Exception:
            return False


class SupermemoryProvider(MemoryProvider):
    """Supermemory hybrid (vector + graph + rules) provider"""
    
    def __init__(self):
        self.config: Optional[dict] = None
        self.vector_store = None
        self.graph_store = None
    
    @property
    def provider_name(self) -> str:
        return "supermemory"
    
    def initialize(self, config: dict) -> bool:
        """Initialize hybrid backend"""
        try:
            import sqlite3
            import json
            
            self.config = config
            db_path = Path(config.get("db_path", "~/.prada/memories/supermemory.db")).expanduser()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # SQLite for rules and metadata
            self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
            cursor = self.conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    memory_type TEXT,
                    vector_embedding TEXT,
                    graph_relations TEXT,
                    rules TEXT,
                    user_id TEXT,
                    created_at REAL
                )
            """)
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Supermemory initialization error: {e}")
            return False
    
    def store(self, target: str, content: str, metadata: dict) -> str:
        """Store hybrid memory"""
        import uuid
        import time
        import json
        
        entry_id = str(uuid.uuid4())[:12]
        now = time.time()
        
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT INTO memories (id, content, memory_type, vector_embedding, graph_relations, rules, user_id, created_at) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (entry_id, content, metadata.get("type", "hybrid"),
             json.dumps(metadata.get("embedding", [])),
             json.dumps(metadata.get("relations", [])),
             json.dumps(metadata.get("rules", [])),
             target, now)
        )
        self.conn.commit()
        return entry_id
    
    def retrieve(self, query: str, limit: int) -> List[MemoryEntry]:
        """Hybrid search (keyword + rules)"""
        import json
        
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT id, content, memory_type, vector_embedding, graph_relations, rules, created_at 
               FROM memories WHERE user_id = ? AND content LIKE ? ORDER BY created_at DESC LIMIT ?""",
            (query, f"%{query}%", limit)
        )
        
        rows = cursor.fetchall()
        entries = []
        for row in rows:
            entries.append(MemoryEntry(
                entry_id=row[0],
                content=row[1],
                metadata={
                    "type": row[2],
                    "embedding": json.loads(row[3] or "[]"),
                    "relations": json.loads(row[4] or "[]"),
                    "rules": json.loads(row[5] or "[]"),
                },
                created_at=row[6],
                updated_at=row[6],
                tags=[],
            ))
        return entries
    
    def update(self, entry_id: str, content: str) -> bool:
        """Update hybrid memory"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("UPDATE memories SET content = ? WHERE id = ?", (content, entry_id))
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def delete(self, entry_id: str) -> bool:
        """Delete hybrid memory"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
            self.conn.commit()
            return True
        except Exception:
            return False


# Provider registry
MEMORY_PROVIDERS = {
    "mem0": Mem0Provider,
    "honcho": HonchoProvider,
    "openviking": OpenVikingProvider,
    "hindsight": HindsightProvider,
    "holographic": HolographicProvider,
    "retaindb": RetainDBProvider,
    "byterover": ByteRoverProvider,
    "supermemory": SupermemoryProvider,
}


def get_memory_provider(name: str) -> Optional[MemoryProvider]:
    """Get memory provider by name"""
    provider_class = MEMORY_PROVIDERS.get(name)
    if provider_class:
        return provider_class()
    return None
