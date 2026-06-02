"""
Compatibility entrypoint for local runs.

This keeps `uvicorn app:app` working while delegating to the maintained
application in `src.main`, whose API routes match the frontend.
"""

from src.main import app


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("src.main:app", host=host, port=port, reload=False)
