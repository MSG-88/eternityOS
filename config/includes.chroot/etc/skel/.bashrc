# ~/.bashrc: executed by bash(1) for non-login shells.  Eternity 08 defaults.

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=2000
HISTFILESIZE=5000
shopt -s checkwinsize

# Eternity 08 prompt: cyan host tag, current directory
PS1='\[\e[36m\]eternity\[\e[0m\]:\[\e[1m\]\w\[\e[0m\]\$ '
case "$TERM" in
    xterm*|rxvt*|*-256color) PS1="\[\e]0;Eternity 08: \w\a\]$PS1" ;;
esac

if [ -x /usr/bin/dircolors ]; then
    eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
fi
alias ll='ls -alF'
alias la='ls -A'

if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    fi
fi

# Local AI toolchain (Python venv with the ML stack) on PATH
if [ -d /opt/eternity/venv/bin ]; then
    case ":$PATH:" in *":/opt/eternity/venv/bin:"*) ;; *) PATH="/opt/eternity/venv/bin:$PATH" ;; esac
fi

# System summary on the first interactive shell of a terminal
if [ -z "$ETERNITY_FETCHED" ] && command -v fastfetch >/dev/null 2>&1; then
    export ETERNITY_FETCHED=1
    fastfetch
fi
