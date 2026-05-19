"""Panel view modules.

Each view module exposes a factory function that returns a callable with the
signature ``(**kwargs) -> tuple[int, str, bytes]`` matching the handler contract
established in ``features/panel/handler.py``.
"""
