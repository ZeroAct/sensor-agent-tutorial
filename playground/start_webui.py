"""Launch Open WebUI with workshop defaults already applied.

Students only fill OPENAI_API_KEY in .env. Groq, Dummy Plant MCP, gpt-oss-20b,
and Groq-TPM-saving flags are set here so Admin → Integrations is not required.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENV_FILE = ROOT / ".env"
DATA_DIR = ROOT / "data" / "open-webui"

MCP_ID = "dummy-plant"
MCP_URL = "http://127.0.0.1:8000/mcp"
DEFAULT_MODEL = "openai/gpt-oss-20b"


def load_dotenv(path: Path = ENV_FILE) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def workshop_settings() -> dict[str, str]:
    model = (os.environ.get("OPENAI_API_MODEL") or DEFAULT_MODEL).strip() or DEFAULT_MODEL
    base_url = (
        os.environ.get("OPENAI_API_BASE_URL") or "https://api.groq.com/openai/v1"
    ).rstrip("/")
    mcp_url = (os.environ.get("MCP_URL") or MCP_URL).strip() or MCP_URL
    data_dir = Path(os.environ.get("DATA_DIR") or DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)

    tool_servers = [
        {
            "type": "mcp",
            "url": mcp_url,
            "path": "",
            "auth_type": "none",
            "key": "",
            "config": {"enable": True},
            "info": {
                "id": MCP_ID,
                "name": "Dummy Plant",
                "description": "10-sensor dummy factory",
            },
        }
    ]
    return {
        "DATA_DIR": str(data_dir),
        "WEBUI_AUTH": "false",
        "ENABLE_LOGIN_FORM": "false",
        "WEBUI_SECRET_KEY": os.environ.get("WEBUI_SECRET_KEY")
        or "workshop-only-not-a-real-secret",
        "ENABLE_PERSISTENT_CONFIG": "false",
        "ENABLE_OLLAMA_API": "false",
        "ENABLE_OPENAI_API": "true",
        "ENABLE_DIRECT_CONNECTIONS": "true",
        "USER_PERMISSIONS_FEATURES_DIRECT_TOOL_SERVERS": "true",
        "USER_PERMISSIONS_FEATURES_WEB_SEARCH": "false",
        "USER_PERMISSIONS_FEATURES_IMAGE_GENERATION": "false",
        "ENABLE_WEB_SEARCH": "false",
        "ENABLE_IMAGE_GENERATION": "false",
        "ENABLE_TITLE_GENERATION": "false",
        "ENABLE_TAGS_GENERATION": "false",
        "ENABLE_FOLLOW_UP_GENERATION": "false",
        "ENABLE_AUTOCOMPLETE_GENERATION": "false",
        "ENABLE_SEARCH_QUERY_GENERATION": "false",
        "ENABLE_RETRIEVAL_QUERY_GENERATION": "false",
        "ENABLE_MEMORIES": "false",
        "OPENAI_API_BASE_URL": base_url,
        "OPENAI_API_BASE_URLS": base_url,
        "OPENAI_API_MODEL": model,
        "OPENAI_API_MODELS": model,
        "DEFAULT_MODELS": model,
        "DEFAULT_PINNED_MODELS": model,
        "MODEL_ORDER_LIST": json.dumps([model]),
        "OPENAI_API_CONFIGS": json.dumps(
            {"0": {"enable": True, "model_ids": [model], "prefix_id": ""}}
        ),
        "TOOL_SERVER_CONNECTIONS": json.dumps(tool_servers, ensure_ascii=False),
        "DEFAULT_MODEL_PARAMS": json.dumps({"function_calling": "native"}),
        "DEFAULT_INTERFACE_SETTINGS": json.dumps(
            {
                "title": {"auto": False},
                "toolIds": [f"server:mcp:{MCP_ID}"],
                "toolServers": [MCP_ID],
            }
        ),
        "DEFAULT_PROMPT_SUGGESTIONS": json.dumps(
            [
                {
                    "title": ["설비와 센서", "목록"],
                    "content": (
                        "지금 플랜트에 설비가 뭐가 있고, 진동 센서는 뭐가 있나요? "
                        "도구로 확인한 뒤 표로 보여 주세요."
                    ),
                },
                {
                    "title": ["pump-a-de", "최신 값"],
                    "content": "pump-a-de의 최신 진동 값. RMS와 시각을 지어내지 말고 도구 결과 그대로.",
                },
            ],
            ensure_ascii=False,
        ),
        "BYPASS_MODEL_ACCESS_CONTROL": "true",
        "DEFAULT_LOCALE": "ko",
        "USER_AGENT": os.environ.get("USER_AGENT") or "Mozilla/5.0 workshop",
    }


def apply_workshop_env() -> dict[str, str]:
    load_dotenv()
    settings = workshop_settings()
    os.environ.update(settings)
    return settings


def main() -> None:
    apply_workshop_env()
    key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if not key:
        raise SystemExit(
            "OPENAI_API_KEY 가 비어 있습니다. playground/.env 에 키를 넣은 뒤 다시 실행하세요."
        )
    host = os.environ.get("WEBUI_HOST", "127.0.0.1")
    port = int(os.environ.get("WEBUI_PORT", "8080"))
    print(f"open-webui  {host}:{port}", flush=True)
    print(f"model       {os.environ['DEFAULT_MODELS']}", flush=True)
    print(f"mcp         {os.environ['TOOL_SERVER_CONNECTIONS']}", flush=True)
    from open_webui import serve

    serve(host=host, port=port)


if __name__ == "__main__":
    sys.exit(main())
