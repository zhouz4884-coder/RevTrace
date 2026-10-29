# Independent metadata-only selection

Final method bdfa is already frozen before reading new corpus selection metadata.
Use only pinned archive member paths, speaker IDs and uncompressed WAV size.
Estimate seconds as (member bytes -44)/32000 without reading WAV content.
Exclude S0764/S0765/S0767/S0768. Try8-9s, only if fewer than four eligible
speakers widen once to8-10s, then8-15s. No further widening. Fixed seed2026102931:
sample four uniformly without replacement from sorted eligible speaker IDs,
preserve draw order, then uniformly choose one member from each speaker's sorted
candidates. Freeze complete eligible pool, initial IDs and fallback order first.

Only after that immutable lock: request four official public ZIP Ranges, check
exact206 offsets/length, local header name/method, central size/CRC, and native
PCM16 mono16k header. No resampling or model calls. Network or CRC failure retries
the same member or stops; it cannot advance selection. Only technical WAV header
failure may move to the next predeclared same-speaker candidate, lexicographically
rotated from the uniformly selected initial position, with every reason retained.
All selected valid sources are retained. Source output/correction/performance is
not available to this program. Reference text is read only after selection lock
to provide CER labels and never influences selection or fallback.

Models/data/cache/raw/logs/audio stay on designated8TB disk. Signed redirects
remain in urllib process memory and are never serialized or printed. GitHub gets
bounded manifests, source, CRC/header/SHA receipts and safe logs, never WAV files.
Warmup for later neural work remains oldsource0, separate from these four new
sources. This acquisition never constructs a neural model or allocates a GPU.

Transport-only recovery v2 keeps the entire metadata lock and source order.
The remote public connection reset after one valid WAV. Official same-byte
Range responses may be fetched through local RAM and transferred directly by
approved SFTP to B; no local audio file is written. Verify staged Range SHA,
length, Content-Range, then the same ZIP CRC/header checks. An already valid
destination WAV is retained only if it equals the fresh exact member bytes;
it is never overwritten or silently substituted. All v1 failure evidence stays.
