# CPU readiness only

Verifies complete source identity, declared package versions, full model asset
bytes, eight existing source WAVs, and GPU-owner inventory without importing a
neural framework or launching inference. Every result is bound to an external
config/prelaunch/source manifest and kept on the designated experiment disk.

Reading weights for SHA256 warms file cache. This check is not evidence of cold
loading, GPU execution, service success, or a reserved exclusive GPU window.
