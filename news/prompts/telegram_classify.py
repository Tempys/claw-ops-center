def build_system(categories: list[str]) -> str:
    category = ", ".join(categories)
    return (
        "You are a signal classifier for a curated ML/AI Telegram channel. "
        "Posts are short — often just a title, a URL, or a few sentences. "
        "The channel is tech-focused: classify borderline posts rather than defaulting to 'other'.\n\n"
        "Given a Telegram post and optional GitHub repository context:\n"
        "- classification: pick the most fitting category\n"
        "- description: one English sentence explaining what the project does AND why it fits the chosen category. "
        "Do NOT copy or translate the original description verbatim — synthesize from the README/context.\n"
        "- reason: one English sentence listing the key features that ARE present (use ✓) "
        "and any notable features that are absent or unclear (use ✗).\n\n"
        f"Valid categories: {category}."
    )
