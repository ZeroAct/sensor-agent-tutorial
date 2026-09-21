"""stdio MCP for Claude Desktop. Shares playground/data/plant.db with `uv run plant`."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "mcp-server"))
    sys.path.insert(0, str(root))
    from server import mcp

    # stdout is the MCP wire. Do not print banners here.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    sys.exit(main())
