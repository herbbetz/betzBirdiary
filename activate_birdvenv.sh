#!/bin/bash
VENVDIR="$HOME/birdvenv"

# ${VIRTUAL_ENV:-} substitutes an empty string if VIRTUAL_ENV is unset, else error: unary operator expected
if [ -d "$VENVDIR" ] && [ "${VIRTUAL_ENV:-}" != "$VENVDIR" ]; then
    source "$VENVDIR/bin/activate"
else
    echo "${0##*/}: Virtual environment not found at $VENVDIR" >&2
fi
