#!/bin/bash
# Desktop launcher for Eternity Chat: run the chat in the terminal and, if it exits with
# an error (model missing, llama.cpp failure), keep the window open so the message is seen
# instead of a window that flashes and closes.
eternity-chat "$@"
rc=$?
if [ "$rc" -ne 0 ]; then
    echo
    echo "eternity-chat exited with status $rc."
    read -r -p "Press Enter to close this window. "
fi
exit "$rc"
