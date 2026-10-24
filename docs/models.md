# Bundled models: research and choice (2026-10-23)

Constraint from the owner: true open licences only (Apache 2.0 / MIT). Meta's
Llama community licence is excluded. Gemma's licence is excluded for the same
reason. CPU-only inference on a 4-core laptop class machine; 4 GB RAM minimum
for the small model, 8 GB recommended for the default.

## Candidates considered (Hugging Face Hub, build day)

| Model | Params | Licence | Q4_K_M size | GGUF source | Notes |
|---|---|---|---|---|---|
| Qwen3.5-4B | 4B dense (hybrid Gated DeltaNet + attention) | Apache 2.0 | 2.74 GB | unsloth/Qwen3.5-4B-GGUF | Released Feb 2026; 7.5M downloads; MMLU-Pro 79.1, MMLU-Redux 88.8 per model card. Text and vision; we use text only. |
| Qwen3.5-2B | 2B dense | Apache 2.0 | 1.28 GB | unsloth/Qwen3.5-2B-GGUF | Same family, same era; fits 4 GB machines. |
| Qwen3-4B-Instruct-2507 | 4B dense | Apache 2.0 | 2.50 GB | unsloth/Qwen3-4B-Instruct-2507-GGUF | Aug 2025; previous generation. Classic transformer, fastest on CPU. Fallback. |
| Qwen3-1.7B | 1.7B dense | Apache 2.0 | 1.11 GB | unsloth/Qwen3-1.7B-GGUF (Qwen's own repo only ships Q8_0) | Previous generation small model. Fallback. |
| Ministral-3-3B-Instruct-2512 | 3B | Apache 2.0 | 2.15 GB | mistralai (own GGUF) | Strong but weaker than Qwen3.5-4B on the published numbers. |
| SmolLM3-3B | 3B | Apache 2.0 | about 1.9 GB | community | Good, but behind Qwen3.5. |
| Phi-4-mini-instruct | 3.8B | MIT | about 2.5 GB | community | Eligible; Feb 2025; behind Qwen3.5 on knowledge benchmarks. |
| Llama 3.2 1B/3B | | Llama community licence | | | Excluded by the owner's licence rule. |
| Gemma 3 1B/4B | | Gemma terms | | | Excluded: not an open licence. |

## Choice for the first iteration

- **default** = `Qwen3.5-4B-Q4_K_M.gguf` (unsloth build of Qwen/Qwen3.5-4B).
- **small** = `Qwen3.5-2B-Q4_K_M.gguf` (unsloth build of Qwen/Qwen3.5-2B).

Why: newest Apache-licensed small models with the best published results in
their size class, same chat template for both, and the author ships the
licence file (`LICENSE` in Qwen/Qwen3.5-4B is Apache 2.0).

Risk and fallback: Qwen3.5 uses a hybrid Gated DeltaNet architecture. llama.cpp
supports it, but CPU throughput may be below the classic Qwen3 transformer. If
`llama-bench` in the smoke test shows under 4 tokens/s for the 4B model on the
build host, or llama.cpp at the pinned tag cannot load the file, the manifest
switches to Qwen3-4B-Instruct-2507 and Qwen3-1.7B (same licence) and this
note is updated.

Thinking mode: Qwen3.5 models reason by default. `eternity-chat` disables
thinking (`enable_thinking=false` via the chat template) so answers come back
promptly on a CPU; `eternity-chat --think` turns it on.

Checksums: computed on the downloaded files by `ai/fetch-models.sh` and
recorded in `ai/models.manifest`; the Hub listing does not expose them.

## Fallback rule evaluated (2026-10-24, build 5 chroot, native)

`llama-bench -p 64 -n 32 -t 4` on the Ryzen 7 3750H: Qwen3.5-4B Q4_K_M generates 6.4
tok/s (prompt 13.5 tok/s); Qwen3.5-2B Q4_K_M generates 12.8 tok/s (prompt 31.7 tok/s).
Both load at llama.cpp `b11843`; the 4B result is above the 4 tok/s threshold, so the
Qwen3.5 pair stays.
