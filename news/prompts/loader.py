from pathlib import Path

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_prompt(name: str, **kwargs: str) -> str:
    template = (_TEMPLATES_DIR / f"{name}.md").read_text(encoding="utf-8")
    return template.format(**kwargs) if kwargs else template
