# PRADA Agent

A self-evolving multi-platform AI agent with closed-loop learning capabilities.

## 🎯 Core Features

1. **🧠 Procedural Memory**: Automatically creates and improves skills from experience
2. **💾 Persistent Memory**: Cross-session user preferences and project context (MEMORY.md + USER.md)
3. **🌐 18+ Message Platforms**: Unified gateway for Telegram/Discord/Slack/WhatsApp/Signal/Matrix/etc.
4. **🖥️ 6 Terminal Backends**: Local/Docker/SSH/Daytona/Modal/Singularity abstraction
5. **🔌 18+ LLM Providers**: Runtime resolution for OpenRouter/OpenAI/Anthropic/Gemini/xAI/etc.
6. **🔄 Built-in Scheduler**: Cron jobs + batch trajectory generation + RL training integration
7. **🔐 Security**: Command approval + credential safety + injection detection + multi-platform authorization

## 📦 Installation

```bash
pip install -e .
```

## 🚀 Quick Start

```bash
# Initialize configuration
prada setup

# Start CLI interface
prada start

# Start message gateway
prada gateway start telegram discord slack
```

## 📚 Documentation

See the [website](website/) directory for full documentation.

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit -q

# Run integration tests (skip live API calls)
pytest tests/integration -m "not live"

# Run E2E tests (requires credentials)
HERMES_LIVE_TESTS=1 pytest tests/e2e --maxfail=1
```

## 🔧 Configuration

Configuration is stored in `~/.prada/`:

- `config.yaml` - Main configuration file
- `.env` - Sensitive credentials (0600 permissions)
- `memories/MEMORY.md` - Agent personal notes
- `memories/USER.md` - User profile
- `skills/` - Skill definitions
- `logs/` - Rotating logs

## 🌟 Key Design Principles

1. **Prompt Stability**: System prompts remain immutable during sessions
2. **Tool Visibility**: All tool executions shown to users via callbacks
3. **Credential Security**: Triple protection (save/load/runtime)
4. **Core-Entry Decoupling**: AIAgent independent of CLI/gateway/ACP/Server
5. **Progressive Loading**: Skills Level 0→1→2, memory frozen at session start
6. **Interruptible Design**: API timeouts, graceful termination, message interruption
7. **Test-First**: 100% unit test coverage, integration + E2E for critical paths
8. **Cross-Platform Consistency**: pathlib everywhere, UTF-8 encoding, unified permissions

## 📋 Supported Platforms

| Platform | Voice | Images | Files | Threads | Reactions | Typing | Streaming |
|----------|-------|--------|-------|---------|-----------|--------|-----------|
| Telegram | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Discord | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WhatsApp | — | ✅ | ✅ | — | — | ✅ | ✅ |
| Signal | — | ✅ | ✅ | — | — | ✅ | ✅ |
| SMS | — | — | — | — | — | — | — |
| Email | — | ✅ | ✅ | ✅ | — | — | — |
| Home Assistant | — | — | — | — | — | — | — |
| Mattermost | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| Matrix | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DingTalk | — | — | — | — | — | ✅ | ✅ |
| Feishu | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| WeCom | ✅ | ✅ | ✅ | — | — | ✅ | ✅ |
| Weixin | ✅ | ✅ | ✅ | — | — | ✅ | ✅ |
| BlueBubbles | — | ✅ | ✅ | — | ✅ | ✅ | — |
| QQBot | ✅ | ✅ | ✅ | — | — | ✅ | — |
| Webhook | — | ✅ | ✅ | — | — | ✅ | ✅ |
| API Server | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 🔧 Tool System

47 tools across 19 toolsets:

- **core**: memory, skill_manage, session_search, usage
- **file**: read_file, write_file, patch, search_files, list_dir
- **terminal**: terminal, process_list, process_kill, process_wait
- **web**: web_search, web_extract, http_request
- **browser**: 10 browser automation tools
- **code**: execute_code, code_analyze, code_fix
- **delegate**: delegate, subagent_status, subagent_cancel
- **mcp**: MCP client integration
- **credentials**: credential_files, env_passthrough
- **vision**: image_analyze, image_generate, audio_transcribe, audio_speak
- **delivery**: send_message, send_file, send_image
- **homeassistant**: 4 HA-specific tools
- **skills**: skills_list, skill_view, skill_manage
- **memory_ops**: memory_add, memory_replace, memory_remove
- **session**: session_list, session_search, session_compress
- **debug**: doctor, logs_tail, config_show
- **rl**: rl_step, rl_reward, rl_trajectory
- **cron**: cron_list, cron_create, cron_delete

## 🧠 Memory System

Two-layer built-in memory + 8 external providers:

### Built-in Memory
- **MEMORY.md**: Agent personal notes (2,200 chars limit)
- **USER.md**: User profile (1,375 chars limit)

### External Providers
- **honcho**: Dialectical user modeling
- **openviking**: Knowledge graph memory
- **mem0**: Semantic vector memory
- **hindsight**: Event timeline memory
- **holographic**: Multimodal holographic memory
- **retaindb**: Relational SQL memory
- **byterover**: Binary code/file memory
- **supermemory**: Hybrid vector+graph+rules

## 🧩 Skill System

Skills follow SKILL.md specification with progressive disclosure:

- **Level 0**: Skill list (~3k tokens) - always injected
- **Level 1**: Full skill content - loaded on demand
- **Level 2**: Reference files - precision loaded

Agents can autonomously create/update skills via `skill_manage` tool.

## 🔄 Cron & Batch Processing

```yaml
# ~/.prada/jobs.json
{
  "jobs": [{
    "id": "daily-backup",
    "schedule": {"type": "cron", "expression": "0 2 * * *"},
    "prompt": "Backup PostgreSQL to S3",
    "toolsets": ["core", "terminal", "file", "delivery"],
    "delivery": {"platform": "telegram", "chat_id": "..."}
  }]
}
```

Batch trajectory generation for training data:

```bash
prada batch run --input prompts.jsonl --output trajectories.jsonl --parallel 4
prada batch compress --input trajectories.jsonl --target-tokens 4096
```

## 🛡️ Security

- **Command Approval**: Dangerous pattern matching with user confirmation
- **Gateway Authorization**: Whitelist + DM pairing dual mechanism
- **Credential Safety**: Non-ASCII filtering, injection detection, Unicode confusion blocking
- **File Permissions**: 0600 for sensitive files, container-aware

## 📈 Monitoring

```bash
prada doctor          # System health check
prada logs --tail     # Real-time log tailing
prada sessions list   # Session history with FTS5 search
prada usage           # Token usage statistics
prada insights --days 7  # 7-day usage analysis
```

## 🚀 Deployment Options

1. **Local**: Direct subprocess execution (default)
2. **Docker**: Container sandbox with volume mounts
3. **SSH**: Remote execution via paramiko
4. **Modal**: Cloud functions with persistent volumes
5. **Daytona**: Workspace-as-a-service
6. **Singularity**: HPC/scientific computing

## 📄 License

MIT License
