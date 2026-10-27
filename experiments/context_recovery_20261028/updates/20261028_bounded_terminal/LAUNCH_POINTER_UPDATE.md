# Current local launch pointer update

The original2026-10-27`SETUP.json` is historical and remains byte-identical:
SHA256`c2c5e7a92089f345bd3bf5825e56e4e4aac72dff57da8b32132f744b3d141fd2`.
It referenced the old LP1starting snapshot7c1765while the clean execution
worktree had advanced to the actually frozen runtimeffaa7a. Thus the original
no-argument gate correctly failed with`HEAD is not the manifest code_commit`.
It must not be “fixed” by resetting the dirty legacy checkout or relabelling
the old manifest.

`CURRENT.json` now supplies an explicitly machine-local current source pointer;
the default CLI validates its stated commit and complete manifest hash. Explicit
source/manifest arguments still validate their actual independent identity,
not the current pointer's commit. Missing or inconsistent current metadata fails
closed. No model, environment, scientific measurement or paper was changed.

The after-check passes218runtime files at
`ffaa7ab41dd8d6099efd0eb9abe2334951dc5932`, manifest SHA256
`487d8289e4eb24126b42f7526f0d1e68fa3afd79374669517cc9dea7518a69c8`.
Existing source/dirty-byte/run-metadata negative tests remain; added fixtures
check the new default pointer hash and explicit historical-input override.
Their recorded CPU execution is a maintenance test, not GPU/serving evidence.
