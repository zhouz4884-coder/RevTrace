# Preserved prelaunch failure

The first invocation of `launch_numeric_v9.py` reached its prelaunch CPU-gate
check before `linux_cpu_v9_native/GATE.json` existed. It raised
`FileNotFoundError`. No numeric result directory, model, GPU Worker or scientific
result was created by that failed invocation. The Linux CPU suite was still
running and subsequently passed332tests/5subtests with zero skips. A fresh
invocation then launched the recorded12row numerical probe normally. This is
a launcher-order error, not a failed numerical/GPU experiment or authentication
problem. The original terminal output was retained in this thread; this note
prevents the attempt from disappearing from the research archive.

The paid waiting-input v8 model-basename failure, native1.5Bmodel/numerical
failures, first paid Whisper capacity failure, earlier CPU failures and the
independent context checker whitespace failure all have their own full frozen
raw records. They are not replaced by later successful gates.
