"""Minimal Hugging Face Space demo. Requires: pip install gradio wanda
NOTE: written but not executed in the build environment (no network). Test before publishing."""
import json
import gradio as gr
from wanda import Normalizer

N = Normalizer()


def run(text, strict):
    n = Normalizer(fuzzy=not strict, min_confidence=N.min_confidence)
    a = n.annotate(text)
    return a["normalized"], a["llm_context"], json.dumps(a["tokens"], ensure_ascii=False, indent=2)


demo = gr.Interface(
    run,
    [gr.Textbox(label="STT transcript (Javanese / dialect)"), gr.Checkbox(label="Strict (exact matches only)")],
    [gr.Textbox(label="Probable Indonesian"), gr.Textbox(label="Context for your LLM"), gr.Code(label="Per-token decisions", language="json")],
    title="Wanda demo (v0.1, unreviewed seed lexicon)",
)

if __name__ == "__main__":
    demo.launch()
