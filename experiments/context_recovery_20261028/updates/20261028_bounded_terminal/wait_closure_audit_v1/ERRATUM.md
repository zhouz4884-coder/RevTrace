# Wait-action counts in v1 are invalid

The v1 independent checker used `event` instead of the actual runtime JSONL
key`kind` when identifying waiting decisions. Its unit fixture repeated that
incorrect schema. Therefore its zero wait/action counts must not be used.
The copied archive hashes, WAL frame/content checks and existing service
metrics are separate and unaffected. The original checker source, successful
but insufficient CPU tests, output and gate remain retained rather than edited.

The correction validates the actual schema, includes a positive active-wait
fixture and fails on missing keys instead of silently returning zero. It is
executed against the same immutable GPU raw without re-running the models.
Use `wait_closure_audit_v2` for the action recount and resulting interpretation.
