"""FastAPI version of the Wanda API (optional: pip install fastapi uvicorn).

    uvicorn wanda.api_fastapi:app --host 127.0.0.1 --port 8080

Same endpoints and behaviour as `wanda serve`, plus automatic OpenAPI docs at /docs.
Not exercised by the default test run unless FastAPI is installed.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .service import Service


def create_app(service: Optional[Service] = None):
    from fastapi import Body, FastAPI
    from fastapi.responses import JSONResponse

    from . import __version__

    svc = service or Service()
    app = FastAPI(title="Wanda API", version=__version__,
                  description="Understanding Javanese and dialect speech. MPL-2.0. No data is stored or sent anywhere.")

    def run(method: str, path: str, payload: Optional[Dict[str, Any]] = None):
        status, body = svc.handle(method, path, payload)
        return JSONResponse(body, status_code=status)

    @app.get("/health")
    def health():
        return run("GET", "/health")

    for route in ("normalize", "annotate", "dialect", "ipa", "morph", "llm-payload", "rescore"):
        def make(r: str):
            def endpoint(payload: Dict[str, Any] = Body(...)):
                return run("POST", f"/v1/{r}", payload)
            endpoint.__name__ = r.replace("-", "_")
            return endpoint
        app.post(f"/v1/{route}")(make(route))
    return app


try:  # allow `uvicorn wanda.api_fastapi:app` without calling create_app() manually
    app = create_app()
except ImportError:  # FastAPI not installed: importing the module stays harmless
    app = None
