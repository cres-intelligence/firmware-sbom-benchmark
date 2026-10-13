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

The two are complementary on purpose. Case 001 is strong evidence with weak provenance: its build
recorded no commit and kept no artifact, so its versions cannot be established and the scorer
refuses to score them. Case 002 records all of it, and so can score the dimensions case 001 cannot.
**The protocol's answer to a gap is to state it, not to fill it with a guess.**

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
  information at all. **One real `.map` file from IAR or armlink, with its recipe, is enough to
  write and test a reader for that format.** A specification is not: LLD's format is documented, and
  the thing that mattered is not something the documentation would have told us.
* **Two architectures.** Cortex-M and RISC-V rv64imac. Nothing big-endian, nothing 8- or 16-bit.
* **Two projects.** FreeRTOS and Mbed TLS. Both widely used in medical device firmware, neither a
  substitute for the breadth a published corpus eventually needs.

**What the four cases establish together**, which no single case could:

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

## Licence boundary

Everything here is specified from **public standards** — CycloneDX, SPDX, NTIA minimum elements,
BSI TR-03183-2 — and from a published benchmark protocol. The projects in the corpus carry their own
upstream licences, recorded per case. No competitor's implementation was read while writing any of
it.
