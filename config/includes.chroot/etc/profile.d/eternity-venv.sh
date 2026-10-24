# Eternity 08: the local AI Python environment is first on PATH for every user.
if [ -d /opt/eternity/venv/bin ]; then
    case ":$PATH:" in
        *":/opt/eternity/venv/bin:"*) ;;
        *) PATH="/opt/eternity/venv/bin:$PATH"; export PATH ;;
    esac
fi
