# Installed formal tools — verified CPU availability

Status: **PASS_TOOLING_ONLY**. All installation and smoke processes completed. No GPU process was started, no system package or shell profile was changed, and no RevTrace study theorem has been run by this task.

Root: `/media/user/5bc0dc8d-c938-4b2a-af1b-94174fc511a9/tools/revtrace_formal_20261027`.

| Component | Actual working version | Location relative to root |
|---|---|---|
| Java | Eclipse Temurin OpenJDK 17.0.17+10 | `temurin17_17.0.17_10/jdk-17.0.17+10-jre/bin/java` |
| TLC | Release 1.7.4; TLC2 Version 2.19, revision 5a47802 | `downloads/tla2tools-1.7.4.jar` |
| TLAPS | 1.5.0, built with OCaml 4.12.0 | `tlaps_1.5.0/bin/tlapm` |
| TLAPS library | Installed standard modules | `tlaps_1.5.0/lib/tlaps` |
| Default SMT backend | Bundled Z3 4.8.9 | resolved by TLAPS local library/bin configuration |
| Other bundled backends | Isabelle2011-1; Zenon 0.8.4 [a268] | resolved by TLAPS local configuration |

Official sources: [TLC 1.7.4](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4), [Temurin 17.0.17+10](https://github.com/adoptium/temurin17-binaries/releases/tag/jdk-17.0.17%2B10), [TLAPS 1.5.0 release](https://github.com/tlaplus/tlapm/releases/tag/202210041448), [official TLAPS Linux installation](https://proofs.tlapl.us/doc/web/content/Download/Binaries/Linux.html).

Verified artifact SHA256:

- TLC jar: `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`; also matches official published SHA1.
- Java archive: `1c607fb19f153b23a7d62ff980eb55cff1a7d47ce565bbc44d14947c93bd33c9`; matches official published SHA256.
- Working TLAPS 1.5.0 installer: `ebb7a3f271bdb564f74cb0a2767ef7b9ff7045621a9be7c50d363a03c2e6f08a`; fixed official release URL, no separate published SHA256 located.
- Rejected TLAPS 1.6.0-pre 2026-10-23 archive: `0d1b393a1042aa08961bb024c784a80a25009a5874258c0ddbbfd95b92e80fe5`; published hash matches, but binary requires glibc versions up to 2.38 unavailable on this host.

The actual system `ldd` reports Ubuntu glibc 2.31. Initial Python `platform` guessed 2.29; the direct system version supersedes that inference. The stable 1.5.0 user-directory install succeeded, including its Isabelle theory build and installer self-test. Optional CVC4/Yices/veriT/SPASS are absent; the default Z3 path works and is the declared smoke backend.

Tool smoke results:

- TLC checked an independent three-state counter: 4 generated states, 3 distinct states, no violation, exit 0.
- TLAPS accepted a set-inclusion implication: 2 obligations proved, exit 0.
- TLAPS rejected `FALSE`: 1/2 obligations failed, exit 3. This is the expected negative smoke result.

The first wrapper incorrectly treated TLC's help exit 1 as a runtime failure; the help content and subsequent real smoke establish normal behavior. Its failed receipt is retained. The stable installer is ELF; the first shell-wrapper help invocation failed and is retained before direct executable help/install succeeded. The first TLC smoke used its default `/tmp` standard-module extraction; final smoke and future commands explicitly set the 8 TB temporary directory. Nothing was erased to hide these setup attempts.

## Exact invocation pattern for later frozen study

Use absolute tool paths; set PATH/TMPDIR only in the subprocess environment. Keep working directory and TLC state path inside a fresh 8 TB result directory.

```text
<java> -Djava.io.tmpdir=<8TB-run-tmp> -XX:+UseParallelGC -Xmx1g -cp <tla2tools-1.7.4.jar> tlc2.TLC -workers 1 -config <frozen.cfg> -metadir <fresh-state-directory> <frozen-module.tla>
<tlapm> --threads 1 --nofp <frozen-proof-module.tla>
```

`--nofp` prevents using prior proof-result fingerprints, though TLAPS still writes its newly produced cache in the run's working directory. `-C` is a separate Isabelle proof-checking option; do not claim it was used for the SMT smoke. A later parameterized study proof must record its actual backend/flags, source/config SHA and full obligations separately from this tool receipt.

Remote receipt: `TOOLING_RECEIPT.json`; retained prior receipts are adjacent. Local bounded copy: `FORMAL_TOOLING_RECEIPT.json`, SHA256 `8c44b4d3b83a7a1f53ab813e5f16beff7ce56330a2b8a8ffac3f6569406c6756`.
