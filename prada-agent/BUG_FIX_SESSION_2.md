# PRADA Agent Bug Fix Report - Session 2025-12-19

## Summary

Fixed critical bugs in OpenRouter and Custom provider resolution, improving error handling and adding support for custom API modes.

---

## Bugs Fixed

### Bug #16: OpenRouter/Custom Provider Resolution Issues

**Symptoms:**
1. `ValueError: CUSTOM_BASE_URL environment variable required for custom provider` when using openrouter provider
2. Confusing timeout errors when API keys were missing
3. No way to specify custom API mode for custom providers

**Root Causes:**
1. `_get_credentials()` function signature didn't accept `provider` parameter, causing issues with credential validation logic
2. Missing API key validation happened too late (after initialization) resulting in cryptic timeout errors
3. Custom provider didn't support `CUSTOM_API_MODE` environment variable for specifying non-standard API formats

**Files Modified:**
- `prada_cli/runtime_provider.py` (3 changes)
- `run_agent.py` (2 changes)

**Changes Made:**

#### 1. Fixed `_get_credentials()` Signature (runtime_provider.py:247)

```python
# Before:
def _get_credentials(provider_info: Dict) -> Dict[str, Optional[str]]:

# After:
def _get_credentials(provider_info: Dict, provider: str = None) -> Dict[str, Optional[str]]:
```

**Reason:** Need provider name to skip warning logs for custom providers (which intentionally don't have predefined env vars)

#### 2. Added CUSTOM_API_MODE Support (runtime_provider.py:190-195)

```python
# For custom provider, also allow custom API mode
custom_api_mode = os.environ.get("CUSTOM_API_MODE", "chat_completions")
if custom_api_mode not in ["chat_completions", "anthropic_messages", "codex_responses"]:
    logger.warning(f"Unknown CUSTOM_API_MODE '{custom_api_mode}', defaulting to chat_completions")
    custom_api_mode = "chat_completions"
api_mode = custom_api_mode
```

**Reason:** Custom providers may use different API formats (Anthropic-style, OpenAI Responses API, etc.)

#### 3. Improved API Key Validation (run_agent.py:169-177)

```python
# Validate API key for non-custom providers
if not api_key and self.provider != "custom":
    env_var = runtime.get('provider_info', {}).get('env_var', 'API_KEY')
    if env_var and not env_var.endswith('?'):
        raise RuntimeError(
            f"API key not found for provider '{self.provider}'. "
            f"Please set the {env_var} environment variable or create a .env file. "
            f"Example: export {env_var}=your-api-key-here"
        )
```

**Reason:** Fail fast with clear error message instead of cryptic timeout errors during API calls

#### 4. Removed Duplicate Validation (run_agent.py:126-135)

Removed redundant API key check that was happening after `_init_client()`, since validation now happens inside `_init_client()`.

---

## Testing

### Test Results

```bash
$ pytest tests/unit -q
56 passed in 2.85s
```

### Manual Testing

#### Test 1: OpenRouter with Missing API Key
```python
>>> resolve_runtime_provider('openrouter', 'minimax/minimax-m2.5:free')
# Logs warning: "Missing required environment variable: OPENROUTER_API_KEY"
# Returns config with api_key=None (will fail fast during agent initialization)
```

✅ **Pass:** Warning logged, resolution succeeds but agent init will fail with clear error

#### Test 2: Custom Provider without CUSTOM_BASE_URL
```python
>>> resolve_runtime_provider('custom', 'my-model')
# Raises: ValueError: CUSTOM_BASE_URL environment variable required for custom provider
```

✅ **Pass:** Clear error message about missing required env var

#### Test 3: Custom Provider with CUSTOM_BASE_URL
```python
>>> os.environ['CUSTOM_BASE_URL'] = 'https://my-custom-api.com/v1'
>>> resolve_runtime_provider('custom', 'my-model')
# Returns: api_mode='chat_completions', base_url='https://my-custom-api.com/v1'
```

✅ **Pass:** Successfully resolves with default API mode

#### Test 4: Custom Provider with CUSTOM_API_MODE
```python
>>> os.environ['CUSTOM_API_MODE'] = 'anthropic_messages'
>>> resolve_runtime_provider('custom', 'my-model')
# Returns: api_mode='anthropic_messages', base_url='https://my-custom-api.com/v1'
```

✅ **Pass:** Custom API mode correctly applied

#### Test 5: Invalid CUSTOM_API_MODE
```python
>>> os.environ['CUSTOM_API_MODE'] = 'invalid_mode'
>>> resolve_runtime_provider('custom', 'my-model')
# Logs warning: "Unknown CUSTOM_API_MODE 'invalid_mode', defaulting to chat_completions"
# Returns: api_mode='chat_completions'
```

✅ **Pass:** Invalid mode defaults safely with warning

---

## Impact

### Before Fix
- ❌ Cryptic `ConnectTimeout` errors when API keys missing
- ❌ No way to use Anthropic/Responses API format with custom providers
- ❌ Confusing error messages for custom provider setup
- ❌ Credential warnings logged even for custom providers (false positives)

### After Fix
- ✅ Clear error messages with exact env var names and examples
- ✅ Full flexibility for custom providers (any API mode + any endpoint)
- ✅ Safe defaults with warnings for invalid configurations
- ✅ No false positive warnings for custom providers

---

## Usage Examples

### Standard Provider (OpenRouter)

```bash
# Set API key
export OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Run agent
prada start --provider openrouter --model minimax/minimax-m2.5:free
```

**Error if missing key:**
```
RuntimeError: API key not found for provider 'openrouter'. 
Please set the OPENROUTER_API_KEY environment variable or create a .env file.
Example: export OPENROUTER_API_KEY=your-api-key-here
```

### Custom Provider (OpenAI-compatible)

```bash
# Set custom endpoint
export CUSTOM_BASE_URL=https://my-company-api.com/v1
export CUSTOM_API_KEY=my-secret-key

# Run agent
prada start --provider custom --model my-custom-model
```

### Custom Provider (Anthropic-compatible)

```bash
# Set custom endpoint with Anthropic API mode
export CUSTOM_BASE_URL=https://my-anthropic-proxy.com/v1
export CUSTOM_API_KEY=my-secret-key
export CUSTOM_API_MODE=anthropic_messages

# Run agent
prada start --provider custom --model claude-3-sonnet
```

### Custom Provider (xAI/Grok Responses API)

```bash
# Set custom endpoint with Responses API mode
export CUSTOM_BASE_URL=https://my-xai-proxy.com/v1
export CUSTOM_API_KEY=my-secret-key
export CUSTOM_API_MODE=codex_responses

# Run agent
prada start --provider custom --model grok-beta
```

---

## Remaining Work

See README.md for full project status. Key remaining items:

1. **CLI Diagnostic Commands** - `prada doctor`, `prada logs`, `prada usage`, `prada insights`
2. **Integration/E2E Tests** - Live API testing, multi-turn conversation tests
3. **ACP Adapter** - VS Code/Zed/JetBrains IDE integration
4. **MCP Client** - Full Model Context Protocol implementation (~2,200 lines)
5. **Docker Image Optimization** - Multi-stage builds, smaller image size
6. **Command Approval System** - Enhanced pattern matching, auto-approve rules
7. **Cron Scheduler** - Full job execution, delivery integration
8. **Documentation** - User guides, best practices, troubleshooting

---

## Conclusion

All critical bugs in provider resolution have been fixed. The agent now:
- Fails fast with clear error messages for missing credentials
- Supports all 3 API modes for custom providers
- Provides helpful setup instructions for new users
- Maintains backward compatibility with all 18+ providers

**Next Priority:** Implement CLI diagnostic commands to help users troubleshoot configuration issues proactively.
