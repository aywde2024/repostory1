"""
PRADA Agent - Web Tools Implementation
Web search, extraction, and HTTP request tools
"""

from typing import Optional, Dict, Any, List
import json
import urllib.parse
from .registry import registry


WEB_SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Search query"},
        "limit": {"type": "integer", "description": "Max results (default: 10)"},
        "engine": {"type": "string", "description": "Search engine: google, bing, duckduckgo (default: google)"},
    },
    "required": ["query"],
}


def web_search_impl(query: str, limit: int = 10, engine: str = "google") -> str:
    """Search the web using specified engine"""
    import requests
    
    engines = {
        "google": "https://www.google.com/search",
        "bing": "https://www.bing.com/search",
        "duckduckgo": "https://html.duckduckgo.com/html",
    }
    
    if engine not in engines:
        return f"Error: Unknown search engine '{engine}'. Available: {list(engines.keys())}"
    
    params = {"q": query, "num": limit}
    
    try:
        response = requests.get(
            engines[engine],
            params=params,
            headers={"User-Agent": "Mozilla/5.0 (Prada Agent)"},
            timeout=30,
        )
        response.raise_for_status()
        
        # Simple parsing (in production, use proper HTML parser)
        results = []
        content = response.text
        
        if engine == "duckduckgo":
            import re
            # Extract result links from DuckDuckGo HTML
            pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
            matches = re.findall(pattern, content)
            for url, title in matches[:limit]:
                results.append(f"- {title}: {url}")
        else:
            # For Google/Bing, extract basic info
            import re
            pattern = r'<cite[^>]*>([^<]+)</cite>'
            cites = re.findall(pattern, content)[:limit]
            for cite in cites:
                results.append(f"- {cite}")
        
        if not results:
            return f"No results found for '{query}'"
        
        return f"Search results for '{query}' ({engine}):\n\n" + "\n".join(results)
    
    except Exception as e:
        return f"Search error: {str(e)}"


WEB_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "URL to extract content from"},
        "selector": {"type": "string", "description": "CSS selector (optional, extracts all if not specified)"},
    },
    "required": ["url"],
}


def web_extract_impl(url: str, selector: Optional[str] = None) -> str:
    """Extract content from a webpage"""
    import requests
    from bs4 import BeautifulSoup
    
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Prada Agent)"}, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        if selector:
            elements = soup.select(selector)
            if not elements:
                return f"No elements found for selector '{selector}'"
            content = "\n".join(elem.get_text(strip=True) for elem in elements)
        else:
            # Extract main content
            # Remove scripts, styles, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Try to find main content area
            main = soup.find('main') or soup.find('article') or soup.body
            content = main.get_text(separator='\n', strip=True) if main else ""
        
        # Limit output length
        max_length = 5000
        if len(content) > max_length:
            content = content[:max_length] + "\n\n[... truncated ...]"
        
        return f"Content from {url}:\n\n{content}"
    
    except Exception as e:
        return f"Extraction error: {str(e)}"


HTTP_REQUEST_SCHEMA = {
    "type": "object",
    "properties": {
        "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE, PATCH"},
        "url": {"type": "string", "description": "Request URL"},
        "headers": {"type": "object", "description": "Request headers (optional)"},
        "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default: 30)"},
    },
    "required": ["method", "url"],
}


def http_request_impl(method: str, url: str, headers: Optional[Dict[str, str]] = None,
                      body: Optional[str] = None, timeout: int = 30) -> str:
    """Make an HTTP request"""
    import requests
    
    method = method.upper()
    if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
        return f"Error: Invalid HTTP method '{method}'"
    
    try:
        kwargs = {
            "timeout": timeout,
            "headers": headers or {},
        }
        
        if method in ["POST", "PUT", "PATCH"] and body:
            # Try to parse as JSON, fallback to text
            try:
                kwargs["json"] = json.loads(body)
            except json.JSONDecodeError:
                kwargs["data"] = body
        
        response = requests.request(method, url, **kwargs)
        
        result_lines = [
            f"Status: {response.status_code}",
            f"Headers: {dict(response.headers)}",
            f"\nBody:\n{response.text}",
        ]
        
        return "\n".join(result_lines)
    
    except Exception as e:
        return f"HTTP request error: {str(e)}"


# Register web tools
registry.register(
    name="web_search",
    func=web_search_impl,
    schema=WEB_SEARCH_SCHEMA,
    toolsets=["web", "core"],
    platforms=["linux", "macos", "windows"],
    requires_env=[],
)

registry.register(
    name="web_extract",
    func=web_extract_impl,
    schema=WEB_EXTRACT_SCHEMA,
    toolsets=["web"],
    platforms=["linux", "macos", "windows"],
    requires_env=["beautifulsoup4"],
)

registry.register(
    name="http_request",
    func=http_request_impl,
    schema=HTTP_REQUEST_SCHEMA,
    toolsets=["web"],
    platforms=["linux", "macos", "windows"],
    dangerous=False,
)
