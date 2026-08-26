"""CodeMason 用户配置管理。

配置文件位置：~/.codemason/config.yaml
凭据文件位置：~/.codemason/credentials.yaml（已有，不改动）

配置结构：
    models:
      main:
        provider: deepseek
        base_url: https://opencode.ai/zen/go/v1
        model: deepseek-v4-flash
        api_key_ref: api_keys.deepseek  # 引用 credentials.yaml 中的 key
      vision:
        provider: mimo
        base_url: https://opencode.ai/zen/go/v1
        model: mimo-v2.5
        api_key_ref: api_keys.mimo
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import yaml


CONFIG_DIR = Path.home() / ".codemason"
CONFIG_PATH = CONFIG_DIR / "config.yaml"
CREDENTIALS_PATH = CONFIG_DIR / "credentials.yaml"


# ========== 默认配置 ==========

DEFAULT_CONFIG: dict[str, Any] = {
    "models": {
        "main": {
            "provider": "deepseek",
            "base_url": "https://opencode.ai/zen/go/v1",
            "model": "deepseek-v4-flash",
            "api_key_ref": "api_keys.deepseek",
        },
        "vision": {
            "provider": "mimo",
            "base_url": "https://opencode.ai/zen/go/v1",
            "model": "mimo-v2.5",
            "api_key_ref": "api_keys.mimo",
        },
    }
}


# ========== 配置读写 ==========

def load_config() -> dict[str, Any]:
    """加载用户配置，不存在则返回默认配置。"""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        # 合并默认值（用户可能只写了部分字段）
        merged = DEFAULT_CONFIG.copy()
        if "models" in data:
            for role, cfg in data["models"].items():
                if role in merged["models"]:
                    merged["models"][role].update(cfg)
                else:
                    merged["models"][role] = cfg
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config: dict[str, Any]) -> None:
    """保存用户配置。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def load_credentials() -> dict[str, str]:
    """加载凭据（api_keys.xxx → 值）。"""
    if not CREDENTIALS_PATH.exists():
        return {}
    try:
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return {k: str(v) for k, v in data.items() if k.startswith("api_keys.")}
    except Exception:
        return {}


def resolve_api_key(ref: str) -> Optional[str]:
    """解析 api_key_ref（如 'api_keys.deepseek'）→ 实际 key 值。

    优先级：环境变量 > credentials.yaml > ref 本身（如果看起来像 key）
    """
    # 1. 环境变量（如 DEEPSEEK_API_KEY）
    env_name = ref.replace("api_keys.", "").upper() + "_API_KEY"
    env_val = os.environ.get(env_name)
    if env_val:
        return env_val

    # 2. credentials.yaml
    creds = load_credentials()
    if ref in creds:
        return creds[ref]

    # 3. 如果 ref 本身像 key（sk-xxx），直接用
    if ref.startswith("sk-"):
        return ref

    return None


# ========== 模型连通性测试 ==========

async def test_model_connection(
    base_url: str,
    model: str,
    api_key: str,
    timeout: float = 10.0,
) -> dict[str, Any]:
    """测试模型连通性：发送一个最小请求，返回结果。

    Returns:
        {
            "ok": True/False,
            "latency_ms": 123,
            "model": "deepseek-v4-flash",
            "provider": "deepseek",
            "error": None 或 "错误信息",
            "response_preview": "你好！..." (前100字符)
        }
    """
    import time

    import httpx

    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 10,
                    "temperature": 0,
                },
            )
            latency_ms = round((time.time() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                content = ""
                if data.get("choices"):
                    content = data["choices"][0].get("message", {}).get("content", "")
                return {
                    "ok": True,
                    "latency_ms": latency_ms,
                    "model": model,
                    "error": None,
                    "response_preview": content[:100],
                }
            else:
                return {
                    "ok": False,
                    "latency_ms": latency_ms,
                    "model": model,
                    "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
                    "response_preview": None,
                }
    except httpx.TimeoutException:
        return {
            "ok": False,
            "latency_ms": round((time.time() - start) * 1000),
            "model": model,
            "error": f"连接超时（{timeout}s）",
            "response_preview": None,
        }
    except Exception as e:
        return {
            "ok": False,
            "latency_ms": round((time.time() - start) * 1000),
            "model": model,
            "error": f"{type(e).__name__}: {e}",
            "response_preview": None,
        }
