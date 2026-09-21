"""stdio MCP for Claude Desktop. Shares playground/data/plant.db with `uv run plant`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("FASTMCP_SHOW_CLI_BANNER", "false")
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def main() -> None:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "mcp-server"))
    sys.path.insert(0, str(root))
    from server import mcp

    # stdout is the MCP JSON-RPC wire. Banners/logs must stay on stderr.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    sys.exit(main())
