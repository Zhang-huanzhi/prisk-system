"""Command entry for the local HTTP API."""

from ..adapters.http_server import build_parser, main

__all__ = ["build_parser", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
