"""Errors that stop the whole run instead of a single row."""


class RunStopError(Exception):
    """Raised when the run cannot continue, e.g. missing file or invalid API key.

    The CLI catches this, prints the message and exits without writing output.
    """
