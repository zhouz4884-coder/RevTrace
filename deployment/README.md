# Deployment records

Store only lightweight topology, package-lock, hardware, and run-manifest
records here. Models, environments, caches, raw traces, and logs remain on the
designated experiment disk.

Every deployed run must identify:

- Git commit and dirty-tree status;
- model ID and local weight hash/commit;
- environment lock;
- GPU model, driver, CUDA, PyTorch, and runtime versions;
- proposer/verifier placement;
- workload manifest hash;
- exact command and frozen config;
- result and log roots.
