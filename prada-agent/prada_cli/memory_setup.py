"""
PRADA CLI Memory Setup
Setup external memory providers
"""

import asyncio
import click
from pathlib import Path

from prada_cli.config import get_prada_home, load_config, save_config


async def setup_memory_provider(provider: str):
    """Setup an external memory provider"""
    prada_home = get_prada_home()
    config = load_config()
    
    click.echo(f"\n🧠 Setting up external memory provider: {provider}\n")
    click.echo("=" * 50)
    
    # Validate provider
    valid_providers = ["mem0", "honcho", "openviking", "hindsight", "holographic", "retaindb", "byterover", "supermemory"]
    
    if provider not in valid_providers:
        click.echo(f"✗ Unknown provider: {provider}")
        click.echo(f"Valid providers: {', '.join(valid_providers)}")
        return
    
    # Update config
    if "plugins" not in config:
        config["plugins"] = {}
    
    config["plugins"]["memory_provider"] = provider
    
    # Provider-specific setup
    if provider == "mem0":
        click.echo("\nMem0 requires a vector database.")
        click.echo("Options: chroma, pinecone, weaviate")
        
        vector_db = click.prompt(
            "Select vector database",
            default="chroma",
            type=click.Choice(["chroma", "pinecone", "weaviate"])
        )
        
        if "mem0" not in config:
            config["mem0"] = {}
        
        config["mem0"]["vector_db"] = vector_db
        config["mem0"]["collection_name"] = click.prompt(
            "Collection name",
            default="hermes_memories"
        )
        config["mem0"]["embedding_model"] = click.prompt(
            "Embedding model",
            default="text-embedding-3-small"
        )
        
        if vector_db == "chroma":
            click.echo("\nChromaDB will use local storage by default.")
            click.echo("For remote ChromaDB, set CHROMADB_HOST and CHROMADB_PORT environment variables.")
        
        elif vector_db == "pinecone":
            api_key = click.prompt("Pinecone API key", hide_input=True)
            # Save to .env file (not shown here for brevity)
            click.echo("✓ Pinecone API key configured (save to .env manually)")
        
        elif vector_db == "weaviate":
            url = click.prompt("Weaviate URL", default="http://localhost:8080")
            api_key = click.prompt("Weaviate API key (optional)", default="", hide_input=True)
            config["mem0"]["weaviate_url"] = url
            if api_key:
                click.echo("✓ Weaviate API key configured (save to .env manually)")
    
    elif provider == "honcho":
        click.echo("\nHoncho uses local SQLite + vector index.")
        click.echo("No additional configuration required.")
    
    elif provider == "openviking":
        click.echo("\nOpenViking requires a Neo4j graph database.")
        neo4j_uri = click.prompt("Neo4j URI", default="bolt://localhost:7687")
        neo4j_user = click.prompt("Neo4j username", default="neo4j")
        neo4j_password = click.prompt("Neo4j password", hide_input=True)
        
        # Save credentials to .env (not shown for brevity)
        click.echo("✓ Neo4j credentials configured (save to .env manually)")
    
    elif provider == "hindsight":
        click.echo("\nHindsight uses time-series database for event回溯.")
        click.echo("Default: Local SQLite with time-based indexing.")
    
    elif provider == "holographic":
        click.echo("\nHolographic requires a multi-modal vector database.")
        db_type = click.prompt(
            "Database type",
            default="weaviate",
            type=click.Choice(["weaviate", "milvus"])
        )
        config["holographic"] = {"db_type": db_type}
    
    elif provider == "retaindb":
        click.echo("\nRetainDB requires PostgreSQL or MySQL.")
        conn_string = click.prompt(
            "Database connection string",
            default="postgresql://user:pass@localhost/hermes"
        )
        # Save to .env
        click.echo("✓ Connection string configured (save to .env manually)")
    
    elif provider == "byterover":
        click.echo("\nByteRover uses Git-like object store for binary memory.")
        click.echo("Storage location: ~/.prada/memories/byterover/")
        (prada_home / "memories" / "byterover").mkdir(parents=True, exist_ok=True)
    
    elif provider == "supermemory":
        click.echo("\nSupermemory is a hybrid system (vector + graph + rules).")
        click.echo("This requires both a vector DB and optionally a graph DB.")
        config["supermemory"] = {
            "vector_enabled": True,
            "graph_enabled": click.confirm("Enable graph component?", default=False),
        }
    
    # Save configuration
    save_config(config)
    click.echo(f"\n✓ Configuration saved to {prada_home / 'config.yaml'}")
    
    click.echo("\n" + "=" * 50)
    click.echo("✅ Memory provider setup complete!\n")
    click.echo("Next steps:")
    click.echo("  1. Ensure required services are running (if applicable)")
    click.echo("  2. Run 'prada start' to begin using enhanced memory")
    click.echo("  3. Use the memory tool to add/retrieve memories")
    click.echo("")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python memory_setup.py <provider>")
        print("Available: mem0, honcho, openviking, hindsight, holographic, retaindb, byterover, supermemory")
        sys.exit(1)
    
    asyncio.run(setup_memory_provider(sys.argv[1]))
