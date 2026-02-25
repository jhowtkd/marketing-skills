def chunk_text(text: str, chunk_size: int = 1000) -> list[str]:
    # Very simple chunker for now
    if not text:
        return []
    return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
