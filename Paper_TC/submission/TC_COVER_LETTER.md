3 September 2026

Editor-in-Chief
IEEE Transactions on Computers

Dear Editor-in-Chief,

Please consider our manuscript, “RevTrace: A Transactional Runtime for
Feedback-State Integrity in Revision-Generative ASR Serving,” as a Regular
Paper in *IEEE Transactions on Computers*.

RevTrace is a runtime-systems contribution rather than a new ASR model. It
identifies a feedback-state integrity failure caused when batch-dependent
accelerator outputs are written into later execution state. To address this
failure, the manuscript introduces Dual-Granularity Feedback Transactions
(DGFT), a versioned state-write authorization protocol, and implements a
parallel proposer–authority runtime. The evaluation covers transaction
integrity, throughput, tail latency, energy, semantic quality, and replica
scaling across Qwen3-ASR and Whisper on RTX 3090 and V100 GPU platforms.

The manuscript makes three principal contributions. First, a causal study
shows that a feedback edge can turn a local execution difference into
persistent state divergence. Second, certificate, parent-version, frontier,
and runtime-configuration binding provide formal accepted-history guarantees.
Third, Coarse authority improves matched-workload throughput by 1.39×/1.28×;
the complete two-plane system reaches up to 6.88× wall-clock speedup over its
per-path all-singleton reference and scales to a balanced eight-V100
configuration. These contributions directly concern runtime systems, parallel
accelerator execution, and the performance and reliability of computer
systems. Streaming ASR is the latency-critical, revision-generative
implementation and evaluation setting; the paper does not claim a new
accelerator architecture, GPU kernel, datacenter-scale deployment, or
multi-node system.

This work is original, is not under consideration elsewhere, and has been
approved by all authors. The authors declare no competing interests.

Sincerely,

Xi Cao
Corresponding author
Beijing University of Chemical Technology
Beijing, China
caoxi@buct.edu.cn
