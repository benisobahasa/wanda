"""Transport-independent request handling shared by the built-in server and the FastAPI app."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import __version__
from .adapters import build_payload
from .dialect import DialectDetector
from .lexicon import Lexicon
from .morphology import analyze as morph_analyze
from .normalizer import Normalizer
from .phonemes import PROFILE_ALIASES, PROFILES, ipa_text
from .rescore import rescore_nbest

MAX_TEXT = 10_000


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _text(payload: Dict[str, Any], key: str = "text") -> str:
    v = payload.get(key)
    if not isinstance(v, str) or not v.strip():
        raise ApiError(f"'{key}' must be a non-empty string")
    if len(v) > MAX_TEXT:
        raise ApiError(f"'{key}' is longer than {MAX_TEXT} characters", 413)
    return v


class Service:
    def __init__(self, lexicon: Optional[Lexicon] = None, lm=None):
        self.lexicon = lexicon or Lexicon.default()
        self.lm = lm

    def _norm(self, payload: Dict[str, Any]) -> Normalizer:
        mc = payload.get("min_confidence", 0.75)
        if not isinstance(mc, (int, float)) or not 0 <= mc <= 1:
            raise ApiError("'min_confidence' must be a number between 0 and 1")
        return Normalizer(self.lexicon, min_confidence=float(mc), fuzzy=not bool(payload.get("strict", False)))

    def handle(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Tuple[int, Dict[str, Any]]:
        payload = payload or {}
        try:
            if method == "GET" and path == "/health":
                rev = sum(1 for e in self.lexicon.entries if e.status == "reviewed")
                return 200, {"status": "ok", "version": __version__, "lexicon_entries": len(self.lexicon), "reviewed_entries": rev}
            if method != "POST":
                raise ApiError("not found", 404)
            if path == "/v1/normalize":
                t = _text(payload)
                return 200, {"normalized": self._norm(payload).normalize(t)}
            if path == "/v1/annotate":
                return 200, self._norm(payload).annotate(_text(payload))
            if path == "/v1/dialect":
                return 200, DialectDetector(self.lexicon).detect(_text(payload)).as_dict()
            if path == "/v1/ipa":
                prof = payload.get("profile", "standard")
                if prof not in PROFILES and prof not in PROFILE_ALIASES:
                    raise ApiError(f"'profile' must be one of {sorted(PROFILES) + sorted(PROFILE_ALIASES)}")
                return 200, {"profile": prof, "words": ipa_text(_text(payload), prof)}
            if path == "/v1/morph":
                w = _text(payload, "word")
                return 200, {"word": w, "analyses": [a.as_dict() for a in morph_analyze(w, self.lexicon)]}
            if path == "/v1/llm-payload":
                try:
                    p = build_payload(_text(payload), payload.get("provider", "generic"), payload.get("model"),
                                      payload.get("language", "id"), self._norm(payload))
                except ValueError as e:
                    raise ApiError(str(e))
                return 200, p
            if path == "/v1/rescore":
                hyps = payload.get("hypotheses")
                if not isinstance(hyps, list) or not hyps or len(hyps) > 100:
                    raise ApiError("'hypotheses' must be a list of 1 to 100 items")
                pairs = []
                for h in hyps:
                    if not isinstance(h, dict) or not isinstance(h.get("text"), str) or not isinstance(h.get("score"), (int, float)):
                        raise ApiError("each hypothesis needs a string 'text' and a numeric 'score'")
                    pairs.append((h["text"], float(h["score"])))
                ranked = rescore_nbest(pairs, self._norm(payload), lm=self.lm)
                return 200, {"ranked": [{"text": t, "score": round(s, 4)} for t, s in ranked]}
            raise ApiError("not found", 404)
        except ApiError as e:
            return e.status, {"error": str(e)}
