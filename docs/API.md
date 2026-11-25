# Wanda JSON API

```bash
pip install -e .
wanda serve --port 8080             # built-in server, standard library only
# or, with FastAPI installed:  pip install fastapi uvicorn
uvicorn wanda.api_fastapi:app --host 127.0.0.1 --port 8080   # docs at /docs
```

The server binds to `127.0.0.1` by default, does not log request bodies (texts may be personal),
stores nothing, and has no authentication. If you expose it beyond your own machine, put it behind
your own TLS and authentication.

| Method and path | Body | Returns |
|---|---|---|
| `GET /health` | none | status, version, lexicon size, reviewed entries |
| `POST /v1/normalize` | `{"text", "strict"?, "min_confidence"?}` | `{"normalized"}` |
| `POST /v1/annotate` | same | per-token decisions plus `llm_context` |
| `POST /v1/dialect` | `{"text"}` | dialect, register, scores, cues |
| `POST /v1/ipa` | `{"text", "profile"?}` | IPA per word |
| `POST /v1/morph` | `{"word"}` | affix analyses |
| `POST /v1/llm-payload` | `{"text", "provider"?, "model"?, "language"?}` | request body for your LLM client |
| `POST /v1/rescore` | `{"hypotheses": [{"text", "score"}]}` | re-ranked hypotheses |

```bash
curl -s localhost:8080/v1/normalize -d '{"text": "kulo mboten ngertos"}'
# {"normalized": "saya tidak tahu"}
```

Limits: 10,000 characters per text and 64 KB per request. Errors are JSON: `{"error": "..."}`.
`/v1/llm-payload` only builds the payload; Wanda never contacts an LLM or stores an API key.
