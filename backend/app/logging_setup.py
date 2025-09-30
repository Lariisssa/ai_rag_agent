import logging
import sys
import structlog


def _redact_embeddings(_logger, _method_name, event_dict):
    """
    Replace any embedding-like content with a placeholder to avoid huge logs.
    Rules:
    - If a key name contains 'embedding', value becomes '(embedding_filtered)'.
    - If a value looks like a long list of numbers, replace with placeholder.
    Applies recursively for nested dicts.
    """

    def redact_value(v):
        # Long numeric vector heuristic
        if isinstance(v, (list, tuple)):
            if len(v) > 32 and all(isinstance(x, (int, float)) for x in v[: min(10, len(v))]):
                return "(embedding_filtered)"
            # Recurse into small lists to keep structure
            return [redact_value(x) for x in v]
        if isinstance(v, str):
            # If it looks like a long bracketed numeric list within a string, redact
            if v.startswith("[") and v.endswith("]") and "," in v and len(v) > 200:
                return "(embedding_filtered)"
            return v
        if isinstance(v, dict):
            return {k: redact_value(val) for k, val in v.items()}
        return v

    out = {}
    for k, v in event_dict.items():
        if isinstance(k, str) and "embedding" in k.lower():
            out[k] = "(embedding_filtered)"
        else:
            out[k] = redact_value(v)
    return out


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO))

    structlog.configure(
        processors=[
            _redact_embeddings,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )
