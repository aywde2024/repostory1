"""
OpenRouter API Integration Tests
Tests for OpenRouter provider resolution and client functionality
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOpenRouterProviderResolution:
    """Test OpenRouter provider resolution logic"""
    
    def test_openrouter_basic_resolution(self):
        """Test basic OpenRouter provider resolution"""
        from prada_cli.runtime_provider import resolve_runtime_provider
        
        result = resolve_runtime_provider("openrouter", "nousresearch/hermes-3-llama-3.1-70b")
        
        assert result["provider"] == "openrouter"
        assert result["model"] == "nousresearch/hermes-3-llama-3.1-70b"
        assert result["api_mode"] == "chat_completions"
        assert result["base_url"] == "https://openrouter.ai/api/v1"
        assert result["credentials"]["auth_type"] == "bearer_token"
    
    def test_openrouter_alias_resolution(self):
        """Test OpenRouter alias 'or' resolution"""
        from prada_cli.runtime_provider import resolve_runtime_provider
        
        result = resolve_runtime_provider("or", "meta-llama/llama-3.1-405b-instruct")
        
        assert result["provider"] == "openrouter"
        assert result["model"] == "meta-llama/llama-3.1-405b-instruct"
        assert result["base_url"] == "https://openrouter.ai/api/v1"
    
    def test_openrouter_env_var(self):
        """Test OpenRouter requires OPENROUTER_API_KEY"""
        from prada_cli.runtime_provider import resolve_runtime_provider
        
        result = resolve_runtime_provider("openrouter", "test-model")
        
        assert result["provider_info"]["env_var"] == "OPENROUTER_API_KEY"
    
    def test_openrouter_api_modes(self):
        """Test OpenRouter supports multiple API modes"""
        from prada_cli.runtime_provider import PROVIDER_FAMILIES
        
        openrouter_info = PROVIDER_FAMILIES["openrouter"]
        assert "chat_completions" in openrouter_info["api_modes"]
        assert "codex_responses" in openrouter_info["api_modes"]


class TestOpenRouterClient:
    """Test OpenRouter ChatCompletions client"""
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test ChatCompletionsClient initialization with OpenRouter"""
        from agent.chat_client import ChatCompletionsClient
        
        client = ChatCompletionsClient(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="nousresearch/hermes-3-llama-3.1-70b"
        )
        
        assert client.api_key == "test-key"
        assert client.base_url == "https://openrouter.ai/api/v1"
        assert client.model == "nousresearch/hermes-3-llama-3.1-70b"
        assert client.timeout == 120
        assert client.max_retries == 3
    
    @pytest.mark.asyncio
    async def test_client_cleanup(self):
        """Test client cleanup method"""
        from agent.chat_client import ChatCompletionsClient
        
        client = ChatCompletionsClient(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1",
            model="test-model"
        )
        
        # Should not raise
        await client.cleanup()
        await client.close()
    
    @pytest.mark.asyncio
    async def test_complete_request_structure(self):
        """Test that complete() builds correct request structure"""
        from agent.chat_client import ChatCompletionsClient
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Test response",
                        "role": "assistant"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"total_tokens": 50}
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client
            
            client = ChatCompletionsClient(
                api_key="test-key",
                base_url="https://openrouter.ai/api/v1",
                model="test-model"
            )
            client._client = mock_client
            
            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ]
            
            result = await client.complete(messages=messages)
            
            # Verify request was made
            assert mock_client.post.called
            call_args = mock_client.post.call_args
            
            # Check endpoint
            assert call_args[0][0] == "/chat/completions"
            
            # Check payload structure
            payload = call_args[1]["json"]
            assert payload["model"] == "test-model"
            assert payload["messages"] == messages
            assert "temperature" in payload
            
            # Check result parsing
            assert result["content"] == "Test response"
            assert result["finish_reason"] == "stop"
            assert result["usage"]["total_tokens"] == 50
    
    @pytest.mark.asyncio
    async def test_complete_with_tools(self):
        """Test complete() with tool calling"""
        from agent.chat_client import ChatCompletionsClient
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "I'll search for you",
                        "tool_calls": [
                            {
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "web_search",
                                    "arguments": '{"query": "test"}'
                                }
                            }
                        ]
                    },
                    "finish_reason": "tool_calls"
                }]
            }
            mock_response.raise_for_status = MagicMock()
            
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.is_closed = False
            mock_client_class.return_value = mock_client
            
            client = ChatCompletionsClient(
                api_key="test-key",
                base_url="https://openrouter.ai/api/v1",
                model="test-model"
            )
            client._client = mock_client
            
            tools = [{
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            }]
            
            result = await client.complete(
                messages=[{"role": "user", "content": "Search for test"}],
                tools=tools
            )
            
            # Verify tools were sent
            payload = mock_client.post.call_args[1]["json"]
            assert "tools" in payload
            assert payload["tool_choice"] == "auto"
            
            # Verify tool calls parsed correctly
            assert "tool_calls" in result
            assert len(result["tool_calls"]) == 1
            assert result["tool_calls"][0]["function"]["name"] == "web_search"


class TestAIAgentWithOpenRouter:
    """Test AIAgent integration with OpenRouter"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization_with_openrouter(self):
        """Test AIAgent initializes correctly with OpenRouter provider"""
        from run_agent import AIAgent
        
        # Mock environment to avoid actual API calls
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            agent = AIAgent(
                provider="openrouter",
                model="nousresearch/hermes-3-llama-3.1-70b",
                toolsets=["core"]
            )
            
            assert agent.provider == "openrouter"
            assert agent.model == "nousresearch/hermes-3-llama-3.1-70b"
            assert agent.toolsets == ["core"]
    
    @pytest.mark.asyncio
    async def test_agent_client_selection(self):
        """Test AIAgent selects correct client for OpenRouter"""
        from run_agent import AIAgent
        
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            agent = AIAgent(provider="openrouter", model="test-model")
            
            # Mock the initialize components to avoid file system operations
            with patch.object(agent, '_load_config', return_value=None):
                with patch('tools.registry.ToolRegistry'):
                    with patch('agent.memory_manager.MemoryManager'):
                        with patch('agent.context_engine.get_context_engine'):
                            with patch('agent.prompt_builder.PromptBuilder'):
                                with patch('agent.chat_client.ChatCompletionsClient') as mock_client:
                                    await agent._init_client()
                                    
                                    # Verify ChatCompletionsClient was used (not Anthropic or Responses)
                                    assert mock_client.called
                                    call_kwargs = mock_client.call_args[1]
                                    assert call_kwargs["api_key"] == "test-key"
                                    assert call_kwargs["base_url"] == "https://openrouter.ai/api/v1"


class TestOpenRouterErrorHandling:
    """Test OpenRouter error handling"""
    
    @pytest.mark.asyncio
    async def test_http_error_retry(self):
        """Test retry logic on HTTP errors"""
        from agent.chat_client import ChatCompletionsClient
        import httpx
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.is_closed = False
            
            # Simulate 2 failures then success
            error_response = MagicMock()
            error_response.status_code = 500
            error_response.text = "Internal Server Error"
            
            success_response = MagicMock()
            success_response.json.return_value = {
                "choices": [{"message": {"content": "Success"}, "finish_reason": "stop"}]
            }
            success_response.raise_for_status = MagicMock()
            
            mock_client.post = AsyncMock(side_effect=[
                httpx.HTTPStatusError("Error", request=MagicMock(), response=error_response),
                httpx.HTTPStatusError("Error", request=MagicMock(), response=error_response),
                success_response
            ])
            
            mock_client_class.return_value = mock_client
            
            client = ChatCompletionsClient(
                api_key="test-key",
                base_url="https://openrouter.ai/api/v1",
                model="test-model",
                max_retries=3
            )
            client._client = mock_client
            
            result = await client.complete(messages=[{"role": "user", "content": "Hi"}])
            
            # Should succeed after retries
            assert result["content"] == "Success"
            assert mock_client.post.call_count == 3
    
    def test_missing_api_key_warning(self, caplog):
        """Test warning when API key is missing"""
        import logging
        from prada_cli.runtime_provider import resolve_runtime_provider
        
        with caplog.at_level(logging.WARNING):
            result = resolve_runtime_provider("openrouter", "test-model")
            
            # Should warn about missing API key
            assert "OPENROUTER_API_KEY" in caplog.text
            assert result["credentials"]["api_key"] is None


class TestOpenRouterModels:
    """Test OpenRouter model listings"""
    
    def test_get_provider_models(self):
        """Test getting available models for OpenRouter"""
        from prada_cli.runtime_provider import get_provider_models
        
        models = get_provider_models("openrouter")
        
        assert isinstance(models, list)
        assert "nousresearch/hermes-3-llama-3.1-70b" in models
        assert "meta-llama/llama-3.1-405b-instruct" in models
    
    def test_get_available_providers(self):
        """Test listing all available providers"""
        from prada_cli.runtime_provider import get_available_providers
        
        providers = get_available_providers()
        
        assert "openrouter" in providers
        assert "or" not in providers  # alias should not be in list
        assert len(providers) >= 18  # At least 18 providers supported


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
