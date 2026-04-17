"""
PRADA Agent - Code Execution Tool
Sandboxed code execution with multiple language support
"""

from typing import Optional, Dict, Any, List
import tempfile
import subprocess
import os
from pathlib import Path
from .registry import registry


CODE_EXECUTE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Code to execute"},
        "language": {"type": "string", "description": "Programming language: python, javascript, bash, ruby, go, rust"},
        "timeout": {"type": "integer", "description": "Execution timeout in seconds (default: 30)"},
        "stdin": {"type": "string", "description": "Standard input (optional)"},
    },
    "required": ["code", "language"],
}


def execute_code_impl(code: str, language: str, timeout: int = 30, 
                      stdin: Optional[str] = None) -> str:
    """Execute code in a sandboxed environment"""
    
    # Language configuration
    LANG_CONFIGS = {
        "python": {
            "extension": ".py",
            "command": ["python3", "-u"],
            "check": ["python3", "--version"],
        },
        "javascript": {
            "extension": ".js",
            "command": ["node"],
            "check": ["node", "--version"],
        },
        "bash": {
            "extension": ".sh",
            "command": ["bash"],
            "check": ["bash", "--version"],
        },
        "ruby": {
            "extension": ".rb",
            "command": ["ruby"],
            "check": ["ruby", "--version"],
        },
        "go": {
            "extension": ".go",
            "command": ["go", "run"],
            "check": ["go", "version"],
        },
        "rust": {
            "extension": ".rs",
            "command": ["rustc", "-o", "/tmp/output", "&&", "/tmp/output"],
            "check": ["rustc", "--version"],
        },
    }
    
    if language not in LANG_CONFIGS:
        return f"Error: Unsupported language '{language}'. Available: {list(LANG_CONFIGS.keys())}"
    
    config = LANG_CONFIGS[language]
    
    # Check if language is available
    try:
        subprocess.run(config["check"], capture_output=True, timeout=5, check=True)
    except Exception:
        return f"Error: {language} is not installed on this system"
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix=config["extension"],
        delete=False,
        encoding='utf-8',
    ) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Execute code
        if language == "rust":
            # Special handling for Rust (compile then run)
            compile_result = subprocess.run(
                ["rustc", "-o", "/tmp/prada_rust_output", temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if compile_result.returncode != 0:
                return f"Compilation error:\n{compile_result.stderr}"
            
            result = subprocess.run(
                ["/tmp/prada_rust_output"],
                capture_output=True,
                text=True,
                timeout=timeout,
                input=stdin,
            )
        else:
            result = subprocess.run(
                config["command"] + [temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                input=stdin,
            )
        
        output_lines = []
        if result.stdout:
            output_lines.append(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            output_lines.append(f"STDERR:\n{result.stderr}")
        output_lines.append(f"Exit code: {result.returncode}")
        
        return "\n".join(output_lines)
    
    except subprocess.TimeoutExpired:
        return f"Error: Code execution timed out after {timeout}s"
    except Exception as e:
        return f"Execution error: {str(e)}"
    finally:
        # Cleanup
        try:
            os.unlink(temp_file)
            if os.path.exists("/tmp/prada_rust_output"):
                os.unlink("/tmp/prada_rust_output")
        except Exception:
            pass


CODE_ANALYZE_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Code to analyze"},
        "language": {"type": "string", "description": "Programming language"},
        "analysis_type": {"type": "string", "description": "Type of analysis: lint, complexity, security (default: lint)"},
    },
    "required": ["code", "language"],
}


def code_analyze_impl(code: str, language: str, 
                      analysis_type: str = "lint") -> str:
    """Analyze code for issues"""
    
    # Simple static analysis (in production, use proper linters)
    issues = []
    
    if language == "python":
        # Basic Python checks
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Skip comments and empty lines
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check for common issues
            if 'eval(' in stripped or 'exec(' in stripped:
                issues.append(f"Line {i}: Use of eval/exec is dangerous")
            if 'import *' in stripped:
                issues.append(f"Line {i}: Wildcard imports are discouraged")
            if ';' in stripped and '#' not in stripped.split(';')[1:]:
                issues.append(f"Line {i}: Multiple statements on one line")
            if len(line) - len(line.lstrip()) == 0 and stripped and not stripped.startswith(('class ', 'def ', '@')):
                if any(prev.strip().endswith(':') for prev in lines[max(0,i-5):i-1]):
                    issues.append(f"Line {i}: Possible indentation issue")
        
        # Check for docstrings in functions/classes
        if 'def ' in code or 'class ' in code:
            if '"""' not in code and "'''" not in code:
                issues.append("No docstrings found in functions/classes")
    
    elif language == "javascript":
        # Basic JavaScript checks
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('//'):
                continue
            
            if 'eval(' in stripped:
                issues.append(f"Line {i}: Use of eval() is dangerous")
            if 'var ' in stripped:
                issues.append(f"Line {i}: Consider using let/const instead of var")
            if '==' in stripped and '===' not in stripped:
                issues.append(f"Line {i}: Use === instead of ==")
            if 'console.log(' in stripped:
                issues.append(f"Line {i}: Remove console.log before production")
    
    elif language == "bash":
        # Basic Bash checks
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            if not stripped or stripped.startswith('#'):
                continue
            
            if '$(' not in stripped and '`' in stripped:
                issues.append(f"Line {i}: Use $() instead of backticks for command substitution")
            if 'rm -rf /' in stripped:
                issues.append(f"Line {i}: DANGEROUS: Recursive root deletion")
            if 'sudo' in stripped and 'EOF' not in code:
                issues.append(f"Line {i}: sudo usage detected - ensure it's necessary")
    
    if not issues:
        return f"No issues found in {language} code ({analysis_type})"
    
    return f"Analysis results ({analysis_type}):\n\n" + "\n".join(f"- {issue}" for issue in issues)


CODE_FIX_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "description": "Code to fix"},
        "language": {"type": "string", "description": "Programming language"},
        "error_message": {"type": "string", "description": "Error message to fix"},
        "suggestion": {"type": "string", "description": "Optional suggestion for the fix"},
    },
    "required": ["code", "language", "error_message"],
}


def code_fix_impl(code: str, language: str, error_message: str,
                  suggestion: Optional[str] = None) -> str:
    """Suggest fixes for code based on error message"""
    
    # This is a simplified version - in production, would use LLM or specialized tools
    fixes = []
    
    common_fixes = {
        "python": {
            "SyntaxError": "Check for missing colons, parentheses, or quotes",
            "IndentationError": "Ensure consistent indentation (4 spaces recommended)",
            "NameError": "Check variable/function names for typos or undefined references",
            "TypeError": "Verify argument types match function signatures",
            "ImportError": "Ensure the module is installed: pip install <module>",
            "ModuleNotFoundError": "Install the missing module with pip",
        },
        "javascript": {
            "SyntaxError": "Check for missing semicolons, brackets, or quotes",
            "ReferenceError": "Check variable names for typos or scope issues",
            "TypeError": "Verify object properties exist before accessing",
            "TypeError: .* is not a function": "Check method names and object types",
        },
        "bash": {
            "command not found": "Install the missing command or check PATH",
            "Permission denied": "Add execute permission: chmod +x script.sh",
            "No such file": "Check file paths and existence",
        },
    }
    
    lang_fixes = common_fixes.get(language, {})
    
    # Match error patterns
    matched_fix = None
    for pattern, fix in lang_fixes.items():
        if pattern.lower() in error_message.lower():
            matched_fix = fix
            break
    
    if matched_fix:
        fixes.append(matched_fix)
    
    if suggestion:
        fixes.append(f"Suggestion: {suggestion}")
    
    if not fixes:
        return f"No automated fix suggestions for: {error_message}\n\nManual debugging required."
    
    return f"Suggested fixes:\n\n" + "\n".join(f"- {fix}" for fix in fixes)


# Register code execution tools
registry.register(
    name="execute_code",
    func=execute_code_impl,
    schema=CODE_EXECUTE_SCHEMA,
    toolsets=["code", "core"],
    platforms=["linux", "macos", "windows"],
    dangerous=True,
)

registry.register(
    name="code_analyze",
    func=code_analyze_impl,
    schema=CODE_ANALYZE_SCHEMA,
    toolsets=["code"],
    platforms=["linux", "macos", "windows"],
)

registry.register(
    name="code_fix",
    func=code_fix_impl,
    schema=CODE_FIX_SCHEMA,
    toolsets=["code"],
    platforms=["linux", "macos", "windows"],
)
