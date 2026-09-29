def frame(event_count: int) -> str:
    """Experimental event-driven frame; never uses a timer."""
    return ("▶", "▷")[event_count % 2]
