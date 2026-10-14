# The firmware SBOM benchmark corpus

**What this is.** Real firmware projects, built reproducibly, each with a hand-established record of
what actually shipped — and a scorer that measures any tool's bill of materials against that record
across eight dimensions.

**Why it exists.** Almost every accuracy figure quoted in this market is unreproducible: a number in
a slide with no corpus behind it. A competitor published an eight-dimension protocol with **no
corpus and no results**, invited submissions, and nobody has submitted. A protocol with nothing to
run it on measures nothing.

**The rule this corpus is built on, and the one most tools fail:**

> **Presence in a source tree is not proof of shipment.** A component list derived from what is
> present is a guess. A component list reconciled against the linker map and the hash of the
> shipped artifact is evidence.

Case 001 exists because of that sentence. Of the 42 FreeRTOS-Plus-TCP translation units the
compiler produced, **seven contributed zero bytes to the image** — IPv6, DHCPv6, two DNS modules,
the IPv4/IPv6 TCP paths and Tiny TCP. A scanner reading the source tree reports those as shipped.
They did not ship. Anything that claims otherwise about this build is measurably wrong, and that is
the point of having a corpus at all.

---

## The cases

| case | what it is for | establishes |
|---|---|---|
| **001** `freertos-plus-tcp-mps2` | Loose object files, and seven compiled translation units the linker discarded | scope, components, provenance |
| **002** `mbedtls-vendor-archive-cortex-m3` | **A vendor `.a`** — `libmbedcrypto.a` with 86 members, of which the image needs 3 | scope, components, **versions**, **licences**, **reproducibility**, **binary binding** |
| **003** `mbedtls-lld-armv7m` | **A different linker.** The byte-identical archive, linked by LLD instead of GNU ld | that the ANSWER is toolchain-independent and the EVIDENCE is not |
| **004** `mbedtls-riscv-rv64imac` | **A different architecture.** The same project on RISC-V, GNU ld | that the answer survives the architecture too — and that the compiler runtime's presence does not |
| **005** `mbedtls-loose-objects-cortex-m3` | **Different packaging.** The byte-identical sources from 002, linked as 108 **loose object files** instead of an archive, with a real `compile_commands.json` | that a build-system provider is what makes case 001's shape readable at all — and that packaging changes nothing about which bytes ship |

The cases are complementary on purpose. Case 001 is strong evidence with weak provenance: its build
recorded no commit and kept no artifact, so its versions cannot be established and the scorer
refuses to score them. Case 002 records all of it, and so can score the dimensions case 001 cannot.
**The protocol's answer to a gap is to state it, not to fill it with a guess.**

### What the corpus has established so far

**Which translation units of a dependency ship is independent of the linker, the architecture AND
the packaging.** Mbed TLS appears in four cases — GNU ld on Cortex-M3 (002), LLD on Cortex-M3 (003),
GNU ld on RISC-V rv64imac (004), and as 108 loose objects on Cortex-M3 (005) — and in every one the
image contains exactly `aes.o`, `sha256.o` and `platform_util.o`. Cases 002 and 005 agree to the
byte: 14,032 for Mbed TLS, 16,184 linked in total.

**Which compiler-runtime helpers ship is NOT independent.** libgcc contributes in 002 and 004 and is
absent from 003, because the helper a target needs is a property of the instruction set.

**And a build provider is not an optimisation, it is the difference between an answer and none.**
On case 005, read from the link map alone: **33.3% recall**. Read with the compilation database:
**66.7%**, the remaining miss being five toolchain startup objects that no compile command accounts
for — which the collector reports as unattributed rather than folding into a neighbour.

## The byte-accounting correction of 2026-10-13

**Both map readers were counting sections that are in the ELF file and not in the device**, and the
corpus's established totals were wrong because of it. Recorded here because the corpus is only worth
anything if its own mistakes are on the record.

| case | was | is | of which was debug information |
|---|---|---|---|
| 001 | 297,027 | **90,445** | 206,582 — 69.5% |
| 002 | 58,291 | **16,184** | 42,107 — 72.2% |
| 004 | 19,848 | **18,200** | 1,648 — 8.3% |

`.debug_*`, `.comment`, `.ARM.attributes` and `.riscv.attributes` are stripped before an image is
flashed. Counting them inflated every figure by an amount that depends on nothing but the
compiler's `-g` setting — so a bill of materials built on those numbers was weighted by each
component's **debug footprint**.

**It inverted a conclusion, which is the part worth dwelling on.** Case 001's ground truth said of
newlib: *"the single largest component in the image at 206KB of 297KB, which is worth knowing before
anybody reports this firmware as mostly FreeRTOS."* newlib carries far more DWARF than FreeRTOS
does. Corrected, newlib is 12,296 bytes of 90,445 — 13.6% — and FreeRTOS-Plus-TCP plus the kernel
are 70,579, which is 78%. **This firmware is mostly FreeRTOS.** The original claim was confident,
quotable, and derived from a measurement nobody had checked against the artefact.

**Three checks would each have caught it, and the one that was done was the one that could not.**

* *Comparing the total against the artefact's own size.* Case 001 records an 80,540-byte `.text` and
  the reader claimed 297,027 linked bytes. Not subtle.
* *Comparing two cases that must agree.* Case 003 recorded Mbed TLS at 14,032 bytes and case 002 at
  14,284 for the identical archive. A 252-byte disagreement sat in the corpus unreconciled, because
  003's figure came from LLD's own `--print-gc-sections` output rather than from the broken reader.
* *Running the parser's cross-implementation test.* `TestItAgreesWithTheEstablishedTotals` compares
  the Go reader against these very figures — and it had been **skipping**, because the collector's
  Makefile mounted only the module directory into the build container, so the corpus was not there
  to read and the run printed `ok`. Both readers shared the defect anyway, so agreement would not
  have caught it; the silent skip is a separate defect and is fixed (`CRES_REQUIRE_CORPUS`).
* *Reconciling the components against the total.* This WAS done, and it passed — to 297,027. An
  internally consistent set of figures can still be measuring the wrong thing. **A reconciliation is
  not a validation.**

The metadata bytes are now reported as `MetadataBytes` rather than dropped, and the previous figures
are kept in each case's `PreviousTotals` so the size of the error stays on the record.

## The eight dimensions

| # | Dimension | What it measures |
|---|---|---|
| 1 | **Component precision and recall** | Against the established inventory, not against another tool |
| 2 | **Version and licence accuracy** | Per component, counted only where the truth is established |
| 3 | **Scope accuracy** | Did the component ship, or was it discarded at link time |
| 4 | **Provenance coverage** | Proportion of reported components carrying inspectable evidence |
| 5 | **Schema validity** | Does the document validate against the standard it claims |
| 6 | **Runtime and memory** | Five or more repetitions, reported with spread |
| 7 | **Reproducibility** | Identical output across equivalent runs |
| 8 | **False positives and negatives** | Named individually, never summarised away |

**All eight are computed.** Dimensions 1–5 and 8 are properties of a **document**, so `score.py`
reads them off the file — dimension 5 by calling the tier's own `schema_validation`, which holds
the published CycloneDX and SPDX schemas, rather than shipping a second validator for two readers
to disagree with.

Dimensions 6 and 7 are properties of a **run**: you cannot read them off an output, you have to
execute the thing. **`run.py`** does that — at least five repetitions, the median wall time with
its spread, peak RSS per repetition, and reproducibility as a digest comparison:

```bash
python3 benchmark/run.py --case 002-mbedtls-vendor-archive-cortex-m3 \
    --command 'my-collector --map {case}/evidence/output.map.gz --out {out}' --repeat 5
```

It refuses rather than producing a meaningless number: **fewer than five repetitions** (the
protocol's floor — one run is an anecdote), **a command without `{out}`** (nothing to score), and
**a tool that exited non-zero** (a partial document parses as a shorter one, so the number would
flatter it). Reproducibility is reported as **yes or no**, never a percentage: either equivalent
runs produced the same bytes or they did not.

## A dimension whose truth is not established is NOT SCORED

This is the corpus's central discipline and it is enforced in code, not by convention.

Every ground-truth field carries a `Confidence`, and `score.py` **refuses to score a dimension
whose truth is `not-established`** — it reports `null` with the reason, and the reason appears in
the output. A corpus that quietly scored 0 for an unknown version would manufacture exactly the
unreproducible number it exists to replace.

So case 001 scores **scope accuracy** — its strongest evidence, straight from the linker map — and
**does not score version accuracy**, because the built tree's commit was not recorded and the
versions therefore cannot be established from what we kept. That gap is stated on the case, not
hidden in it. It is also the first thing to fix, and `BUILD.md` says how.

| Confidence | Meaning |
|---|---|
| `pinned` | Established from build output — the linker map, the artifact hash. A fact. |
| `indexed` | Established from a curated index entry verified against an upstream authority. |
| `heuristic` | Inferred. Scoreable, but the inference is recorded beside it. |
| `not-established` | Not known. **Never scored.** The note says what would establish it. |

## Running it

```bash
cd cres-aws-t4
python3 benchmark/score.py --case 001-freertos-plus-tcp-mps2 --sbom path/to/candidate.cdx.json
```

The candidate may be CycloneDX or SPDX, in JSON or XML — it is read with the same parser the tier
ingests supplier documents with. Add `--runtime-seconds` and `--repeat-digests` to score dimensions
6 and 7 from a harness that actually ran the tool.

```bash
python3 benchmark/score.py --case 001-... --sbom a.json --json   # machine-readable
python3 benchmark/score.py --list                                # the cases
```

## Adding a case

A case is a directory under `cases/` holding:

* **`case.json`** — identity, toolchain, the exact build recipe, and the artifacts produced.
* **`ground-truth.json`** — the components, each with scope, confidence and the evidence behind it.
* **`BUILD.md`** — reproduction from nothing, including the container, so somebody else gets the
  same bytes.
* **`evidence/`** — the build output the truth was derived from. The linker map at minimum.

**Ground truth is derived from build evidence, never from a tool's output.** A corpus whose truth
came from a scanner measures agreement with that scanner, which is worth nothing. Where a judgement
was made rather than a fact recorded, it goes in `Uncertainty` on the component — for example
`smsc9220_eth_drv.o` in case 001, which is a vendor Ethernet driver vendored inside
FreeRTOS-Plus-TCP's portable layer: whether a bill of materials should list it separately is a
judgement, and it is written down as one.

## What this corpus does not yet cover

Stated here because a corpus's limits are part of its result:

* **No IAR, armlink or TI.** All three are proprietary and licence-gated; none could be built here,
  and a plausible map written from their documentation would be the unreproducible evidence this
  corpus exists to replace. Case 003 covers a non-GNU linker instead (LLD), which established that
  **the answer is toolchain-independent and the evidence is not** — an LLD map carries no discard
  information at all.

  **The discard information may not be in the map at all, which changes what to ask for.** A
  practitioner pointed out that IAR's ILINK takes `--log sections`, which logs the section
  selection the linker performed rather than only the layout it arrived at; `--log
  unused_fragments` looks like the companion for what section-fragment elimination removed.
  **Neither has been seen here** — there is no IAR installation to run, and a reader written from
  that description alone would be the same unreproducible evidence as a map written from a
  specification. It is recorded because it moves the ask: for IAR the useful artefact is probably
  **the map together with the `--log sections` output**, not the map alone. armlink's equivalent is
  still an open question, `--info unused` being the obvious candidate.

  **One real set of those files from a build somebody is already licensed to run, with its recipe,
  is enough to write and test a reader.** A specification is not: LLD's format is documented, and
  the thing that mattered is not something the documentation would have told us.
* **Two architectures.** Cortex-M and RISC-V rv64imac. Nothing big-endian, nothing 8- or 16-bit.
* **Two projects.** FreeRTOS and Mbed TLS. Both widely used in medical device firmware, neither a
  substitute for the breadth a published corpus eventually needs.

**What these three cases establish together**, which no single case could:

| | 002 Cortex-M, GNU ld | 003 Cortex-M, LLD | 004 RISC-V, GNU ld |
|---|---|---|---|
| members pulled in | **aes, platform_util, sha256** | **the same three** | **the same three** |
| libgcc in the image | yes (division helpers) | **no** | yes (`__bswapsi2`) |

**"Which archive members ship" is independent of the linker and of the architecture** — three
independent confirmations rather than an assumption. **Which compiler-runtime helpers ship is
not**: libgcc is a component of two of the three images and of neither the source tree nor any
manifest.
* **No comparison yet.** Nothing has been scored against this. Syft and Trivy are not firmware
  tools, but running them anyway and publishing what happens is worth doing.

## Where this is published, and how to keep it that way

The corpus is public at **https://github.com/cres-intelligence/firmware-sbom-benchmark**, under
Apache-2.0 (see `LICENSE` and `NOTICE`, which say what the licence does and does not cover).

**IT IS PUBLISHED AS A GIT SUBTREE OF THIS DIRECTORY, not copied.** This directory stays the
working copy, because two consumers read it from here by relative path -- `cres-aws-t4`'s Python
suite at `benchmark/cases`, and `cres-collector`'s Makefile at `../cres-aws-t4/benchmark/cases`.
Moving it would break both, and two independent copies of a corpus is how two copies quietly stop
agreeing.

To publish a change, from the repository root:

```bash
git subtree push --prefix=benchmark \
    https://github.com/cres-intelligence/firmware-sbom-benchmark.git master
```

**A change committed here is not a published one until that runs.** If the public copy is behind,
that command is the whole fix; the history is shared, so it fast-forwards.

## Licence boundary

Everything here is specified from **public standards** — CycloneDX, SPDX, NTIA minimum elements,
BSI TR-03183-2 — and from a published benchmark protocol. The projects in the corpus carry their own
upstream licences, recorded per case. No competitor's implementation was read while writing any of
it.
