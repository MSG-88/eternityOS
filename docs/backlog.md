# Eternity 08 backlog (items the owner asked to carry into later phases)

- **Cloud agents next to the local models (phase 2).** Add an option to integrate
  subscription-based agents (Claude, ChatGPT) directly into the OS in addition to the
  bundled in-house LLM models. Design direction: a provider layer under `eternity-chat` /
  `eternity-ai` that targets the local `llama-server` by default and, when the user adds
  their own subscription credentials, a cloud agent (Claude via the Claude API or Claude
  Code; ChatGPT via OpenAI); offline falls back to local. Requested 2026-10-24.
