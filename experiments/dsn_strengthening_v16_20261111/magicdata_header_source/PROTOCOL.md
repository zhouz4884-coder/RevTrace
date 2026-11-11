# Official MAGICDATA test-only header readiness

This source contains two separate CPU modes. `controls` runs12 synthetic
RIFF/archive/transport controls and joins the frozen official metadata only.
`acquire_census` additionally downloads ONLY the original official test archive,
then scans every original WAV member's RIFF chunks without decoding samples.
TRANS is never opened or parsed. No train/dev member or model call is allowed.

Pin HTTPS URLs, expected2,201,936,013bytes, the observedETag, metadata archive,
test.scp and SPKINFO hashes. The official landing page links no checksum; bounded
adjacent md5sum.txt/md5sum/sha256sum.txt probes returned404. Therefore expected
official checksum is explicitly absent unless later verified. Compute SHA256
andMD5 after complete transport; do not call observed hash official verification.

HTTP resumes require exact206, Content-Range/Length and unchangedETag. A partial
transport remains in its owned raw folder; it never becomes a successful census.
Full gzip EOF validatesCRC/ISIZE; tar headers/path/type checks forbid traversal,
links/special/sparse members andtrain/dev. Every24279expected test basename is
unique and joins the exact43official test speaker IDs; missing/extra fail.

WAV analysis uses declaredRIFF size and allchunk lengths/padding, not44bytes.
Accept candidate format only monoPCM16/16kHz with consistentblockalign/byterate;
PCM extensible format is checked byGUID and validbits. Unknown/JUNK/LIST chunks
are skipped. Multipledata, duplicatefmt, truncation and invalidsizes are technical
rejects. Unsupportedcodec duration remainsunknown. No trimming, resampling or
concatenation. Duration bins are[6,12)and[12,20], exactheaderframes/samplerate.

Keep original2.20GBarchive and perWAVheaders/byte hashes on8TB. Hashing discarded
payload bytes establishes identity without decoding or semantic inspection.
Only bounded aggregate counts return locally. Report all43candidate counts,
including0. There is NO actual16speaker selection orunused/pretraining claim:
fresh complete experimental-historycensus remains required.

Everymode has frozenconfig/env/fullcodecommit/manifest, prelaunchrecord and8TB
raw/summary/gate. DefaultCURRENT is a separate machine-local execution pointer;
record its observedidentity before/after, never reset or rewrite it for this CPU
source. Root coordinates acquisition with GPUdriveractivation and profiles.

Run/event/progress records includeUTC, monotonic time, perprocessIO/CPU/faults,
globalcache/vmstat snapshots. Hashing and scanning warm caches and spendIO;
these periods cannot be mislabeled coldGPUconstructor trials. No cache eviction,
unrelatedprocesssignals, GPU imports or extra device are used.
