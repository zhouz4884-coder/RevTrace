# CPU fixture temp-directory failure, not a protocol/GPU result

CPU_ROLE_AND_OPERATOR_v3 retained11passes/8setup errors:Windows managed-sandbox
pytest default Temp could not allocate a numbered directory after10tries. The
eight fixtures did not execute, so this file is not counted as19passes. Previous
v2 had19passes before test-path portability changes. No GPU probe was launched.

The frozen source f0eaae69323fbaa10b3892761a8ac2c149181013 was then tested directly
with a fresh explicitly scoped workspace basetemp, after verifying it did not
exist. No old temp tree/user files were deleted; no runtime algorithm changed.
The v4 fresh basetemp also failed at setup because its parent directory was
absent. Creating ONLY the workspace tmp parent, then using a new nonexisting
v5 basetemp, passed19/19 on the exact frozen source; no production code changed.
Final record is CPU_ROLE_AND_OPERATOR_FROZEN_v5.xml. Keep both setup-failure XML
and this distinction in artifact delivery. Future freeze/launch gates must read
the exact final XML counts instead of relying on a preceding shell command's
intent; PowerShell does not automatically stop on native command failure.
