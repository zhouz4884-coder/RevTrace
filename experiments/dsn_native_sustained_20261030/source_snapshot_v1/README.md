# Frozen sustained-input data tools

Pure-standard-library metadata selection, exact official public ZIP extraction,
PCM16/mono16k verification and no-gap same-speaker utterance concatenation.
The fixed study selects two unused speakers and 24 utterances per speaker from
8–12s uncompressed-size metadata, without content/model outcome selection.
There is no source replacement fallback: transport retries the exact Range;
CRC/header/reference failure stops. New WAVs and all ranges stay on the8TB disk.

These are explicitly **synthetic concatenated utterances**, not natural long
recordings. Only the final synthetic stream end is EOS; no reset/silence is added
at part boundaries. Final neural runtime identity is frozen separately; this
selection does not pretend the final resilience implementation was already fixed.

`select_recipe.py --config RULE --manifest SOURCE` freezes the recipe before
any audio/reference text is read. `acquire_recipe.py --config PLAN --manifest
SOURCE` executes only in the root-allocated remote IO window. Neither tool
imports a model or Torch. The previous bdfa method remains separately identified.
