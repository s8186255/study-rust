# maf-python-agent 公共库：config.json 加载 + OpenAI 兼容客户端工厂
# 与 maf-csharp-agent / study-agent 的配置机制对齐：改配置切换模型服务，业务代码不动
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from agent_framework.openai import OpenAIChatCompletionClient

# Windows 控制台默认 cp1252/cp936，统一改 UTF-8 避免中文打印报错
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


@dataclass
class AgentConfig:
    base_url: str = "http://10.126.126.2:8089/v1"
    api_key: str = ""
    model: str = "gemma-4-26B-A4B"
    temperature: float = 0.7


def _find_config() -> Path:
    """从入口脚本（sys.argv[0]）所在目录向上查找 config.json"""
    entry = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path.cwd()
    for d in [entry.parent, *entry.parent.parents]:
        candidate = d / "config.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError("未找到 config.json（从入口脚本目录向上查找）")


def load_config(config_path: str | Path | None = None) -> AgentConfig:
    path = Path(config_path) if config_path else _find_config()
    data = json.loads(path.read_text(encoding="utf-8"))
    return AgentConfig(
        base_url=data.get("base_url", AgentConfig.base_url),
        api_key=data.get("api_key", "") or "EMPTY",
        model=data.get("model", AgentConfig.model),
        temperature=float(data.get("temperature", AgentConfig.temperature)),
    )


def get_client(config_path: str | Path | None = None):
    """返回 (OpenAIChatClient, AgentConfig)，配置从 lab 目录下的 config.json 读取"""
    cfg = load_config(config_path)
    client = OpenAIChatCompletionClient(
        model=cfg.model,
        api_key=cfg.api_key,
        base_url=cfg.base_url,
    )
    return client, cfg
