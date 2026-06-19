"""Command-line entry point: ``opspilot`` boots the web server."""

from __future__ import annotations

import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="opspilot",
        description="Deploy-in-a-day natural-language analytics over messy data.",
    )
    # Cloud hosts (Render, Cloud Run, HF Spaces, Fly) inject $PORT; bind 0.0.0.0
    # there so the container is reachable. Locally it defaults to 127.0.0.1:8050.
    in_cloud = "PORT" in os.environ
    parser.add_argument(
        "--host", default="0.0.0.0" if in_cloud else "127.0.0.1", help="Bind host."
    )
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PORT", "8050")), help="Bind port."
    )
    args = parser.parse_args()

    print(f"OpsPilot running at http://{args.host}:{args.port}")
    uvicorn.run("opspilot.app:app", host=args.host, port=args.port)


if __name__ == "__main__":  # pragma: no cover
    main()
