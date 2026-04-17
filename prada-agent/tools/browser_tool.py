"""
PRADA Agent - Browser Automation Tools
Supports multiple backends: Playwright, Selenium, Puppeteer
"""

from typing import Optional, Dict, Any, List
from .registry import registry


# Browser state storage (per session)
_browser_sessions: Dict[str, dict] = {}


BROWSER_NAVIGATE_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "URL to navigate to"},
        "session_id": {"type": "string", "description": "Browser session ID (optional, creates new if not provided)"},
        "timeout": {"type": "integer", "description": "Navigation timeout in ms (default: 30000)"},
    },
    "required": ["url"],
}


def browser_navigate_impl(url: str, session_id: Optional[str] = None, timeout: int = 30000) -> str:
    """Navigate browser to a URL"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return "Error: Playwright not installed. Install with: pip install playwright"
    
    # Create or get session
    if not session_id:
        import uuid
        session_id = str(uuid.uuid4())[:8]
    
    if session_id not in _browser_sessions:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _browser_sessions[session_id] = {
            "playwright": playwright,
            "browser": browser,
            "page": page,
        }
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        page.goto(url, timeout=timeout)
        title = page.title()
        return f"Navigated to {url}\nPage title: {title}\nSession ID: {session_id}"
    except Exception as e:
        return f"Navigation error: {str(e)}"


BROWSER_CLICK_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {"type": "string", "description": "CSS selector of element to click"},
        "session_id": {"type": "string", "description": "Browser session ID"},
    },
    "required": ["selector", "session_id"],
}


def browser_click_impl(selector: str, session_id: str) -> str:
    """Click an element on the page"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        page.click(selector)
        return f"Clicked element: {selector}"
    except Exception as e:
        return f"Click error: {str(e)}"


BROWSER_FILL_SCHEMA = {
    "type": "object",
    "properties": {
        "selector": {"type": "string", "description": "CSS selector of input element"},
        "value": {"type": "string", "description": "Text to fill"},
        "session_id": {"type": "string", "description": "Browser session ID"},
    },
    "required": ["selector", "value", "session_id"],
}


def browser_fill_impl(selector: str, value: str, session_id: str) -> str:
    """Fill text into an input element"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        page.fill(selector, value)
        return f"Filled '{value}' into: {selector}"
    except Exception as e:
        return f"Fill error: {str(e)}"


BROWSER_EVALUATE_SCHEMA = {
    "type": "object",
    "properties": {
        "javascript": {"type": "string", "description": "JavaScript code to execute"},
        "session_id": {"type": "string", "description": "Browser session ID"},
    },
    "required": ["javascript", "session_id"],
}


def browser_evaluate_impl(javascript: str, session_id: str) -> str:
    """Execute JavaScript in the browser context"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        result = page.evaluate(javascript)
        return f"JavaScript result:\n{result}"
    except Exception as e:
        return f"Evaluate error: {str(e)}"


BROWSER_SCREENSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {"type": "string", "description": "Browser session ID"},
        "path": {"type": "string", "description": "File path to save screenshot (optional)"},
        "full_page": {"type": "boolean", "description": "Capture full page (default: false)"},
    },
    "required": ["session_id"],
}


def browser_screenshot_impl(session_id: str, path: Optional[str] = None, 
                            full_page: bool = False) -> str:
    """Take a screenshot of the current page"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        screenshot = page.screenshot(full_page=full_page, path=path)
        
        if path:
            return f"Screenshot saved to: {path}"
        else:
            # Return base64 encoded image
            import base64
            b64 = base64.b64encode(screenshot).decode()
            return f"Screenshot (base64, first 200 chars):\n{b64[:200]}..."
    except Exception as e:
        return f"Screenshot error: {str(e)}"


BROWSER_DOWNLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string", "description": "URL of file to download"},
        "path": {"type": "string", "description": "Local path to save file"},
        "session_id": {"type": "string", "description": "Browser session ID"},
    },
    "required": ["url", "path"],
}


def browser_download_impl(url: str, path: str, session_id: Optional[str] = None) -> str:
    """Download a file from URL"""
    import requests
    
    try:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return f"Downloaded {url} to {path}"
    except Exception as e:
        return f"Download error: {str(e)}"


BROWSER_UPLOAD_SCHEMA = {
    "type": "object",
    "properties": {
        "file_path": {"type": "string", "description": "Local file path to upload"},
        "selector": {"type": "string", "description": "File input CSS selector"},
        "session_id": {"type": "string", "description": "Browser session ID"},
    },
    "required": ["file_path", "selector", "session_id"],
}


def browser_upload_impl(file_path: str, selector: str, session_id: str) -> str:
    """Upload a file to a file input element"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    try:
        page.set_input_files(selector, file_path)
        return f"Uploaded {file_path} to {selector}"
    except Exception as e:
        return f"Upload error: {str(e)}"


BROWSER_TAB_MANAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "description": "Action: new, close, switch, list"},
        "session_id": {"type": "string", "description": "Browser session ID"},
        "index": {"type": "integer", "description": "Tab index (for switch/close)"},
        "url": {"type": "string", "description": "URL for new tab"},
    },
    "required": ["action", "session_id"],
}


def browser_tab_manage_impl(action: str, session_id: str, 
                           index: Optional[int] = None,
                           url: Optional[str] = None) -> str:
    """Manage browser tabs"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    browser = session["browser"]
    page = session["page"]
    
    try:
        if action == "list":
            contexts = browser.contexts
            tabs_info = []
            for i, ctx in enumerate(contexts):
                pages = ctx.pages
                for j, p in enumerate(pages):
                    tabs_info.append(f"Tab {i}.{j}: {p.url} - {p.title()}")
            return "Open tabs:\n" + "\n".join(tabs_info)
        
        elif action == "new":
            if not url:
                return "Error: URL required for new tab"
            new_page = browser.new_page()
            new_page.goto(url)
            return f"Created new tab: {url}"
        
        elif action == "close":
            if index is None:
                page.close()
                return "Closed current tab"
            else:
                contexts = browser.contexts
                if len(contexts) > index:
                    contexts[index].pages[0].close()
                    return f"Closed tab {index}"
                return f"Error: Tab {index} not found"
        
        elif action == "switch":
            if index is None:
                return "Error: Index required for switch"
            contexts = browser.contexts
            if len(contexts) > index:
                session["page"] = contexts[index].pages[0]
                return f"Switched to tab {index}"
            return f"Error: Tab {index} not found"
        
        else:
            return f"Error: Unknown action '{action}'"
    
    except Exception as e:
        return f"Tab management error: {str(e)}"


BROWSER_HISTORY_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {"type": "string", "description": "Browser session ID"},
        "limit": {"type": "integer", "description": "Max history entries (default: 10)"},
    },
    "required": ["session_id"],
}


def browser_history_impl(session_id: str, limit: int = 10) -> str:
    """Get browser navigation history"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    
    # Note: Playwright doesn't expose full history, just current page info
    try:
        current_url = page.url
        title = page.title()
        return f"Current page:\nURL: {current_url}\nTitle: {title}\n\nNote: Full history not available in Playwright"
    except Exception as e:
        return f"History error: {str(e)}"


BROWSER_COOKIES_SCHEMA = {
    "type": "object",
    "properties": {
        "session_id": {"type": "string", "description": "Browser session ID"},
        "action": {"type": "string", "description": "Action: get, set, delete, clear"},
        "name": {"type": "string", "description": "Cookie name (for set/delete)"},
        "value": {"type": "string", "description": "Cookie value (for set)"},
        "url": {"type": "string", "description": "Cookie URL (for set)"},
    },
    "required": ["action", "session_id"],
}


def browser_cookies_impl(action: str, session_id: str,
                         name: Optional[str] = None,
                         value: Optional[str] = None,
                         url: Optional[str] = None) -> str:
    """Manage browser cookies"""
    if session_id not in _browser_sessions:
        return f"Error: Session '{session_id}' not found"
    
    session = _browser_sessions[session_id]
    page = session["page"]
    context = page.context
    
    try:
        if action == "get":
            cookies = context.cookies()
            if name:
                cookies = [c for c in cookies if c["name"] == name]
            return f"Cookies:\n{cookies}"
        
        elif action == "set":
            if not all([name, value, url]):
                return "Error: name, value, and url required for set"
            context.add_cookies([{"name": name, "value": value, "url": url}])
            return f"Set cookie: {name}={value}"
        
        elif action == "delete":
            if not name:
                return "Error: name required for delete"
            cookies = context.cookies()
            filtered = [c for c in cookies if c["name"] != name]
            context.clear_cookies()
            context.add_cookies(filtered)
            return f"Deleted cookie: {name}"
        
        elif action == "clear":
            context.clear_cookies()
            return "Cleared all cookies"
        
        else:
            return f"Error: Unknown action '{action}'"
    
    except Exception as e:
        return f"Cookie error: {str(e)}"


# Register browser tools
browser_tools = [
    ("browser_navigate", browser_navigate_impl, BROWSER_NAVIGATE_SCHEMA),
    ("browser_click", browser_click_impl, BROWSER_CLICK_SCHEMA),
    ("browser_fill", browser_fill_impl, BROWSER_FILL_SCHEMA),
    ("browser_evaluate", browser_evaluate_impl, BROWSER_EVALUATE_SCHEMA),
    ("browser_screenshot", browser_screenshot_impl, BROWSER_SCREENSHOT_SCHEMA),
    ("browser_download", browser_download_impl, BROWSER_DOWNLOAD_SCHEMA),
    ("browser_upload", browser_upload_impl, BROWSER_UPLOAD_SCHEMA),
    ("browser_tab_manage", browser_tab_manage_impl, BROWSER_TAB_MANAGE_SCHEMA),
    ("browser_history", browser_history_impl, BROWSER_HISTORY_SCHEMA),
    ("browser_cookies", browser_cookies_impl, BROWSER_COOKIES_SCHEMA),
]

for name, func, schema in browser_tools:
    registry.register(
        name=name,
        func=func,
        schema=schema,
        toolsets=["browser"],
        platforms=["linux", "macos", "windows"],
        requires_env=["playwright"],
    )
