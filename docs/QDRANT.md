# Qdrant facts for PageSight

Checked on 2026-10-04 from public web pages and source code only (nothing installed or run); source URLs are listed
at the bottom. "Unverified" = no official source confirms it. "Estimate" = our own arithmetic.

## 1. Versions

- Server: latest stable `v1.19.1`, published 2026-09-04 ([releases]). Client: `qdrant-client` 1.19.1, on PyPI since
  2026-09-16, requires Python >= 3.10 and lists 3.10 to 3.14, so 3.11 is supported ([pypi]).
- Compatibility: client SDKs are tested against the latest 3 minor server versions ([upgrades]); the client only warns
  (`UserWarning`) if the majors differ or the minors differ by more than 1; `check_compatibility=False` skips the
  check (`common/version_check.py` in [client-src]).
- Docker image `qdrant/qdrant:v1.19.1`, linux/amd64: 74,114,133 bytes compressed (70.68 MB on Docker Hub) ([hub]).

## 2. Multivectors and MaxSim

- A *multivector* is a matrix of vectors in one point; *MaxSim* adds up, over the query vectors, each one's best
  similarity with the point's vectors ([vectors]). A *named vector* is one of several vector fields of a point; both
  go in `create_collection(..., vectors_config={"patches": ..., "pooled": ...})` ([vectors], [collections]):
  - "patches": `models.VectorParams(size=128, distance=models.Distance.DOT, hnsw_config=models.HnswConfigDiff(m=0),
    multivector_config=models.MultiVectorConfig(comparator=models.MultiVectorComparator.MAX_SIM))`
  - "pooled": `models.VectorParams(size=128, distance=models.Distance.DOT)`
- Distance: Cosine "is implemented as dot-product over normalized vectors", and vectors "are automatically normalized
  during upload" ([collections]). For our unit-length vectors `DOT` gives exactly the sum of max dot products, like
  our brute force; Cosine would re-normalize the bf16-rounded vectors and shift scores slightly (estimate).
- *HNSW* is the graph index for fast approximate search. Docs: "Disable the HNSW index for vectors used only for
  rescoring by setting `m=0`" ([hybrid]).
- Datatypes (`datatype=`): `FLOAT32` (default), `FLOAT16` (half the memory), `UINT8` (0 to 255 only, not for signed
  vectors), `TURBO4` (4 bits per dimension, v1.19.0+) ([vectors]); `TURBO4` on a multivector is in a tutorial
  ([turbo4]); float16/uint8 multivector storage is in `vector_storage_base.rs` ([server-src]), not in the docs.
- Limits: `number_of_sub_vectors * vector_size < 1,048,576`, so at most 8,191 vectors of 128-d per point; ours have
  up to 1,139 ([vectors]). REST bodies: `service.max_request_size_mb: 32` by default ([config]). gRPC has no cap: the
  server sets `max_decoding_message_size(usize::MAX)` (`src/tonic/mod.rs` in [server-src]) and the Python client sets
  both gRPC message-length limits to -1 (`connection.py` in [client-src]).

## 3. Quantization on multivectors

- *Quantization* keeps a compressed copy of each vector for fast scoring (int8: 1 byte per dimension; binary: 1 bit);
  *rescoring* re-scores the top candidates with the originals; *oversampling* fetches extra candidates first. Qdrant's
  course applies int8 and binary to a 128-d MaxSim multivector, using `rescore=True, oversampling=2.0` ([q-course]).
- Binary: 1-bit since v1.5.0; `encoding=models.BinaryQuantizationEncoding.TWO_BITS` or `ONE_AND_HALF_BITS` since
  v1.15.0 (16x and 24x compression, vs 32x); asymmetric (queries encoded more finely than stored vectors)
  `query_encoding=models.BinaryQuantizationQueryEncoding.SCALAR8BITS` or `SCALAR4BITS` since v1.15.0; TurboQuant since
  v1.18.0. 1-bit loses precision "for vectors smaller than a thousand dimensions"; ours are 128-d ([quantization]).
- Per query: `models.QuantizationSearchParams(ignore=..., rescore=..., oversampling=...)` inside `SearchParams`.
  Rescoring is on by default for binary; `ignore=True` skips the quantized copy, so one collection can serve both
  "none" and "binary" ([quantization]); each `Prefetch` has its own `params` ([hybrid]). Unverified: whether the final
  MaxSim re-score of prefetched candidates reads quantized or original vectors.
- Later changes: `update_collection(quantization_config=...)` adds or changes quantization (per named vector via
  `models.VectorParamsDiff`); `models.Disabled.DISABLED` removes it; `create_vector_name(...)` adds a named vector
  (v1.18.0+; existing points stay empty until upserted) ([quantization], [collections]). Open bug (2026-09-29): adding
  a multivector to an already indexed collection breaks segment merges on 1.19.0 and 1.19.1 ([issue-10857]).
- ColPali reports: binary with rescoring ~2x faster than int8, "similar accuracy", no figures ([colpali-bq]). Row
  mean-pooling (~1,030 to 38 vectors/page), prefetch 200, rerank 20, 20,000+ pages: 13x faster, NDCG@20 0.952 and
  Recall@20 0.917 vs original ColPali (reference not stated) ([colpali-13x]); pooling to 32 vectors kept quality
  "comparable to the original model" ([pdf-tutorial]); `TURBO4` kept 99.6% of NDCG@20 on 96-d ColBERT ([turbo4]).

## 4. Embedded local mode (`QdrantClient(path=...)` or `QdrantClient(":memory:")`)

- Runs inside Python with no server; the README suggests it for "development, prototyping and testing" and states no
  limits ([pypi]). From `qdrant_client/local/` ([client-src]): MAX_SIM multivectors and `query_points` with `prefetch`
  work; a quantization config is accepted and silently ignored (unused `**kwargs`; `update_collection` applies only
  sparse vectors and metadata); search is exact brute force and `search_params` "has no effect".
- Points are pickled into a SQLite file per collection (`storage.sqlite`); dense vectors sit in RAM as float32 NumPy
  arrays; one process per folder. A warning fires above `LARGE_DATA_THRESHOLD = 20_000` points; it counts points, so
  our 4,052 pages pass silently with ~2.2 GB of float32 in RAM (estimate).

## 5. Docker on Windows

- Qdrant needs "block-level access to storage devices with a POSIX-compatible file system"; "Using Docker/WSL on
  Windows with mounts is known to have file system problems causing data loss" ([install]); on Windows use a *named
  volume* (managed by Docker), not a *bind mount* of a Windows folder ([quickstart]). Docker Desktop's disk image can
  be moved (Settings > Resources > Advanced) ([docker-settings]). Checked on this laptop: `docker volume inspect` puts
  volumes under `/var/lib/docker/volumes/`, inside Docker's 16.6 GB data disk `docker_data.vhdx` on C:.
- Ports: 6333 REST (and web UI at `/dashboard`), 6334 gRPC, 6335 distributed; mount `/qdrant/storage` ([install],
  [quickstart]). No authentication by default ([quickstart]); publish as `-p 127.0.0.1:6333:6333` to stay local
  ([docker-ports]). Telemetry off: `QDRANT__TELEMETRY_DISABLED=true` ([telemetry]).
- Memory: since v1.19.0 each structure has a tier, `memory=models.Memory.PINNED` (kept in RAM), `CACHED` (pre-loaded
  into the disk cache, can be evicted) or `COLD` (read from disk on first use); `on_disk` and `always_ram` are
  deprecated ([tiers], [releases]). Defaults: vectors cached, quantized vectors pinned ([tiers]). "Original cold,
  quantized pinned" is the docs' balanced mode ([quantization]).

## Implications for PageSight

- Pin `qdrant/qdrant:v1.19.1` and `qdrant-client==1.19.1`. Use `DOT` and `m=0` on "patches"; create "patches" and
  "pooled" together (open bug above). "pooled" is a mean of unit vectors (length below 1), so Dot and Cosine rank it
  differently: choose on dev. As a dense vector it needs one query vector, e.g. the mean of the query tokens.
- Upload over gRPC with `timeout=` set (with `timeout=None` gRPC calls get 5 s, `qdrant_remote.py` in [client-src]).
  Estimate: a finance page is 1,139 x 128 x 4 = 583,168 B as float32 but ~1.5 to 2.9 MB as JSON text, so REST with
  the default `upload_points(batch_size=64)` would exceed 32 MB.
- Measure "none" vs "binary" on the Docker server (local mode ignores quantization; D-024, D-025). 1-bit is weakest
  at 128-d: log `rescore` and `oversampling` with every run; if 1-bit fails on dev, 2-bit, 1.5-bit, `SCALAR8BITS`
  queries or int8 are config changes, not re-embedding.
- Storage estimate, vectors only (no index, payload or log overhead), for 4,322,188 vectors (1,110 x 875 + 2,942 x
  1,139). Quantized copies sit next to the originals ([quantization]): "binary" = float32 on disk + 69 MB in RAM.

| float32 (512 B/vector) | float16 (256 B) | int8 (128 B) | 1-bit binary (16 B) |
| --- | --- | --- | --- |
| 2,212,960,256 B = 2.21 GB | 1,106,480,128 B = 1.11 GB | 553,240,064 B = 0.55 GB | 69,155,008 B = 69 MB |

- Measured after indexing (results/qdrant_index.json, bytes allocated once settled): float32 originals 2.21 GB,
  binary copy 69 MB, whole collections 2.39 GB (hr 0.57 GB, finance_en 1.83 GB; most of the rest is the WAL, the
  write-ahead log). Two traps: right after a collection turns green, segments the optimizer replaced are still on disk
  for a few seconds (hr read 2.38 GB, then 0.57 GB); and the apparent size (`du -b`) counts space Qdrant reserves in
  advance (a 64-page probe: 1.03 GB apparent, 68 MB allocated).

[releases]: https://github.com/qdrant/qdrant/releases
[pypi]: https://pypi.org/pypi/qdrant-client/1.19.1/json
[upgrades]: https://qdrant.tech/documentation/upgrades/
[client-src]: https://github.com/qdrant/qdrant-client/tree/master/qdrant_client
[hub]: https://hub.docker.com/v2/repositories/qdrant/qdrant/tags/v1.19.1
[vectors]: https://qdrant.tech/documentation/manage-data/vectors/
[collections]: https://qdrant.tech/documentation/manage-data/collections/
[hybrid]: https://qdrant.tech/documentation/search/hybrid-queries/
[turbo4]: https://qdrant.tech/documentation/tutorials-search-engineering/turbo4-multivector-search/
[server-src]: https://github.com/qdrant/qdrant/tree/v1.19.1
[config]: https://qdrant.tech/documentation/ops-configuration/configuration/
[q-course]: https://qdrant.tech/course/multi-vector-search/module-3/quantization-techniques/
[quantization]: https://qdrant.tech/documentation/manage-data/quantization/
[issue-10857]: https://github.com/qdrant/qdrant/issues/10857
[colpali-bq]: https://qdrant.tech/blog/qdrant-colpali/
[colpali-13x]: https://qdrant.tech/blog/colpali-qdrant-optimization/
[pdf-tutorial]: https://qdrant.tech/documentation/tutorials-search-engineering/pdf-retrieval-at-scale/
[install]: https://qdrant.tech/documentation/installation/
[quickstart]: https://qdrant.tech/documentation/quickstart/
[docker-settings]: https://docs.docker.com/desktop/settings-and-maintenance/settings/
[docker-ports]: https://docs.docker.com/engine/network/port-publishing/
[telemetry]: https://qdrant.tech/documentation/ops-configuration/usage-statistics/
[tiers]: https://qdrant.tech/documentation/ops-configuration/memory-tiers/
