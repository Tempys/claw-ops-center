# Prompt .md Files + Loader Design

## Goal

Move prompt strings out of Python source files and into `.md` template files, with a dedicated loader that handles both static and parameterized prompts.

## Directory Structure

```
news/prompts/
  __init__.py          # re-exports load_prompt
  loader.py            # implementation
  templates/
    email_classify.md  # static prompt
    telegram_classify.md  # prompt with {categories} placeholder
```

Files removed: `news/prompts/email_classify.py`, `news/prompts/telegram_classify.py`

## Loader

`load_prompt(name: str, **kwargs: str) -> str` in `loader.py`:
- Reads `news/prompts/templates/{name}.md`
- If kwargs provided, applies `template.format(**kwargs)`
- Raises `FileNotFoundError` on missing template (fail-fast, no silent fallback)

`__init__.py` re-exports `load_prompt` so callers use `from news.prompts import load_prompt`.

## Template Format

Plain markdown/text. Dynamic values use standard Python `{placeholder}` syntax. Example in `telegram_classify.md`:

```
Valid categories: {categories}.
```

## Caller Changes

**`news/nodes/email_analyzer.py`**
```python
from news.prompts import load_prompt
_EMAIL_SYSTEM = load_prompt("email_classify")
```

**`news/nodes/telegram_analyzer.py`**
```python
from news.prompts import load_prompt
_SYSTEM = load_prompt("telegram_classify", categories=", ".join(list(get_args(...))))
```

The `build_system` function is deleted — its category-joining logic moves inline to the caller.

## Tests

No test imports change. `test_email_analyzer.py` imports `_EMAIL_SYSTEM` from the node, which still works after the node is updated.
