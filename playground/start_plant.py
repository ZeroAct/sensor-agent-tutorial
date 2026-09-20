"""Start the dummy factory + MCP server."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root / "mcp-server"))
    sys.path.insert(0, str(root))
    from server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
