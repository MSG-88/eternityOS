# Eternity 08 bundled models

GGUF files for llama.cpp. `default.gguf` and `small.gguf` are symlinks to the
bundled files; `models.json` describes them; `SHA256SUMS` verifies them;
each `*.LICENSE` is the model's licence text (Apache 2.0).

Use: `eternity-chat` (interactive), `eternity-chat --ask "..."`,
`eternity-ai models`. Add your own GGUF here and run
`eternity-chat --model /opt/eternity/models/your.gguf`.
