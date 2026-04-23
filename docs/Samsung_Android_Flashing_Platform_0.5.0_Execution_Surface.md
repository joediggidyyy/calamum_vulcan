# Calamum Vulcan — Samsung-focused Android Flashing Platform `0.5.0` Execution Surface

## Sprint shell document

- **Release target:** `0.5.0`
- **Sprint position:** Sprint 5 of 6
- **Roadmap stage:** Stage III — Transport Autonomy
- **Sprint theme:** efficient integrated transport extraction
- **Current backend posture:** Sprint 4 still leaves Heimdall as delegated lower transport for the standard Samsung download-mode detect and bounded write lane. Sprint 5 is no longer obligated to restore full polished functionality one sprint early; it is obligated to pull the supported-path transport behind a Calamum-owned runtime boundary as efficiently as possible. Embedded Heimdall-derived internals remain acceptable if they preserve functionality better than a premature clean-room rewrite.
- **Publication posture:** `0.5.0` is a package-only sprint boundary. Renewed TestPyPI/PyPI publication remains deferred until the immediate post-`0.6.0` `1.0.0` promotion gate.
- **Document purpose:** define the execution shell, scope boundaries, stack decomposition, and validation grammar for Sprint 5 under the updated roadmap where efficiency of extraction outranks temporary completeness.
- **Authority rule:** this document defines the Sprint 5 goal; current implementation evidence measures status against it and may not redefine it just because the carried system drifted.

## Sprint thesis

`0.5.0` has to answer five questions before Sprint 6 can credibly close a fully functional Calamum-owned integrated Samsung runtime with no required external Heimdall installation:

1. **Which Samsung runtime responsibilities must be extracted now to make `0.6.0` realistic rather than aspirational?**
   Sprint 5 has to identify and land the minimum supported-path seams that collapse the remaining **external** Heimdall runtime surface decisively.
2. **How much temporary incompleteness is acceptable if it shortens the path to Sprint 6?**
   The sprint should optimize for structural progress, not for polishing every intermediate behavior back to a public-ready state.
3. **Where does Heimdall-derived logic get embedded, and where does Heimdall remain reference, oracle, or fallback rather than active product direction?**
   Any remaining Heimdall use has to be explicit, temporary, and justified against the Sprint 6 target, while embedded reuse stays acceptable only when Calamum owns the packaged runtime boundary.
4. **What proof is sufficient for a package-ready Sprint 5 candidate?**
   The sprint still needs deterministic evidence, installable artifacts, and honest pre-package notes even without renewed registry publication.
5. **What must be handed forward to `0.6.0` and `1.0.0` without ambiguity?**
   Sprint 5 has to leave a bounded closeout list rather than another open-ended exploration lane.

By the end of this sprint, the platform should be able to say all of the following with evidence:

- Calamum-owned supported-path seams exist for Samsung download-mode detect/identity, PIT acquisition/comparison, and write-path orchestration on the supported lane, even if some internals remain Heimdall-derived
- no new core feature depends on deeper Heimdall integration than the Sprint 4 posture already carried
- any remaining Heimdall use is explicit and framed as reference, fallback, migration aid, or regression oracle rather than hidden product authority
- the `0.5.0` candidate can be marked package-ready as a package-only sprint milestone even if it is not yet the first fully restored polished flashing boundary
- the remaining gap to `0.6.0` is specific enough to treat Sprint 6 as a closeout sprint rather than another discovery sprint

## What `0.5.0` is trying to prove

Sprint 5 is **not** trying to prove that the product is already the final polished Samsung flasher. It is trying to prove these narrower but more strategic claims:

1. efficient structural extraction matters more than temporary completeness at this boundary
2. Calamum-owned integrated Samsung runtime seams now outrank incremental Heimdall polishing as the main delivery priority
3. regression oracle and fallback discipline can stay explicit while the platform removes **external Heimdall dependence** from the supported runtime path
4. the Sprint 5 package boundary can remain honest without pretending it is the public `1.0.0` promotion boundary

## Core sprint identity

| Surface                                 | `0.5.0` identity                                                                                                                                                                                                                  |
| --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| version boundary                        | Sprint 5 / Stage III / `0.5.0`                                                                                                                                                                                                    |
| sprint role                             | extract the remaining supported-path seams that make a fully functional Calamum-owned integrated runtime achievable in Sprint 6                                                                                                   |
| autonomy position                       | deeper than Sprint 4 delegated safe-path extraction, but intentionally allowed to be less polished than the final Sprint 6 supported runtime                                                                                      |
| primary operator promise                | the operator and reviewer can see which Samsung runtime responsibilities are now Calamum-owned, which still remain externally delegated, and where embedded Heimdall-derived logic is being used intentionally rather than hidden |
| differentiator focus                    | structural extraction, explicit external-dependency demotion, bounded fallback truth, and honest package-only closure                                                                                                             |
| major carry-forward debt addressed here | detect/PIT/write seam internalization, regression-oracle discipline, and a bounded closeout list for Sprint 6                                                                                                                     |
| explicit non-goal                       | claiming Sprint 5 is already the first fully restored, fully polished, publicly promoted flashing boundary                                                                                                                        |

## In-scope outcomes

### 1) Supported-path download-mode detect and identity extraction

Sprint 5 should extract the Samsung download-mode detect and identity lane far enough that an external Heimdall executable no longer defines the primary reviewed truth for supported-path device presence and identity.

### 2) Supported-path PIT acquisition, parsing, and comparison ownership

The platform should absorb the remaining PIT responsibilities that still materially block Sprint 6 closure, including acquisition, parse truth, and comparison behavior where those surfaces still depend on an externally delegated Heimdall runtime.

### 3) Supported-path write-path seam extraction

Sprint 5 should move the write-path contract inward so the platform owns the boundary that matters most: flash-plan execution supervision, transfer-state grammar, and the seams needed to eliminate the **external** Heimdall requirement in Sprint 6 without another major discovery phase.

### 4) External Heimdall demotion and regression-oracle discipline

Any continued **external** Heimdall usage should be reduced to explicit fallback, migration comparison, or regression-oracle roles. Sprint 5 may embed or vendor Heimdall-derived internals where that shortens the path without sacrificing functionality, but it should stop adding new operator-visible or deployment-visible dependence on the standalone Heimdall tool.

### 5) Package-only `0.5.0` boundary with explicit carry-forward

The sprint should still close as a real version boundary with artifacts, hashes, validation evidence, and honest support wording. But that closeout is package-only: renewed TestPyPI/PyPI publication stays outside the Sprint 5 boundary.

## Cross-cutting validation grammar for Sprint 5

The standing validation grammar for Sprint 5 is:

- targeted `pytest` and contract coverage for every new native seam
- deterministic source-tree plus installed-artifact proof for the bounded Sprint 5 surface
- adversarial parser and execution-path testing wherever native seams replace delegated ones
- explicit comparison or parity checks against Heimdall outputs when those checks reduce Sprint 6 risk
- package-boundary freeze proof with aligned versioning, hashes, notes, and carry-forward surfaces
- no renewed TestPyPI/PyPI publication as part of the Sprint 5 closeout criteria

## Explicit non-goals

To keep the sprint honest, the following are out of scope unless a later stack deliberately promotes them:

- claiming `0.5.0` is already the default polished public flashing boundary on the supported matrix
- reopening PyPI publication before the immediate post-`0.6.0` `1.0.0` promotion gate
- broad host-matrix expansion that does not directly reduce the Sprint 6 autonomy risk
- cosmetic polish work that does not materially support native seam extraction or closeout honesty
- treating strict clean-room Heimdall separation as a success criterion if embedded Heimdall-derived transport reuse preserves functionality better while still collapsing the external dependency

## Active authority surfaces for the sprint

The active local authority set for Sprint 5 should be treated as:

- `docs/Samsung_Android_Flashing_Platform_Research_Report_and_Build_Plan.md`
- `docs/Samsung_Android_Flashing_Platform_0.4.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.4.0_Closeout_and_Prepackage_Checklist.md`
- `docs/Samsung_Android_Flashing_Platform_0.5.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_0.6.0_Execution_Surface.md`
- `docs/Samsung_Android_Flashing_Platform_1.0.0_Promotion_Gate.md`

## Workstream layout for Sprint 5

| Lane   | Focus                                                                            |
| ------ | -------------------------------------------------------------------------------- |
| Lane A | supported-path Samsung download-mode detect and identity extraction              |
| Lane B | supported-path PIT acquisition, parsing, and alignment ownership                 |
| Lane C | supported-path write-path seam extraction and supervised execution grammar       |
| Lane D | external Heimdall demotion, regression-oracle discipline, and fallback isolation |
| Lane E | package-only closeout, evidence integrity, and Sprint 6 handoff                  |

## Frame-stack decomposition for `0.5.0`

| Stack    | Focus                                                                                              | Why it is its own stop point                                                                      |
| -------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `FS5-01` | foundation declarations and safe-path acceptance criteria                                          | pins the sprint grammar and ownership surfaces before deeper extraction begins                    |
| `FS5-02` | session-layer authority and launch-state extraction                                                | makes reviewed/live/fallback launch-state truth authoritative                                     |
| `FS5-03` | device/package/PIT alignment hardening                                                             | turns descriptive alignment truth into stronger gating before deeper runtime work                 |
| `FS5-04` | fallback identity and fastboot session extraction                                                  | keeps delegated and fallback lanes explicit as the supported path narrows                         |
| `FS5-05` | bounded safe-path transport responsibility                                                         | promotes one narrow reviewed execute lane into platform-supervised grammar                        |
| `FS5-06` | runtime hygiene, transcript policy, and operator-surface honesty                                   | keeps logs, recovery, and GUI/CLI surfaces trustworthy as transport ownership expands             |
| `FS5-07` | selective fallback discipline, broad security gate, empirical closure, and sprint-close evidence   | consolidates the candidate proof pack before any boundary move                                    |
| `FS5-08` | pre-package checklist, package-ready freeze, package-only boundary execution, and Sprint 6 handoff | makes package-ready explicit before any later seal step and hands remaining autonomy work forward |

## Entry criteria

Sprint 5 can open on the assumption that:

- the Sprint 4 shell has already made delegated lower transport and package-only closure explicit
- the remaining Heimdall runtime surfaces are known well enough to target direct displacement instead of vague modernization
- renewed TestPyPI/PyPI publication remains out of scope for the sprint
- the validated local runtime for Calamum work remains the approved `.venv-core` environment

## Exit criteria

Sprint 5 should not be considered fully closed until all of the following are true:

- Calamum-owned supported-path seams for the remaining Samsung runtime responsibilities exist and are testable
- Sprint 5 has not deepened product coupling to Heimdall beyond the carried Sprint 4 posture
- any remaining external Heimdall usage is explicitly labeled as fallback, oracle, migration aid, or temporary extraction debt, and any embedded Heimdall-derived core is packaged as Calamum-owned runtime implementation rather than external prerequisite
- the remaining Sprint 6 autonomy list is bounded and concrete
- the `0.5.0` candidate is package-ready with package artifacts, hashes, evidence, and honest carry-forward notes, and any later repo-visible seal step remains explicit rather than implied
- renewed TestPyPI/PyPI publication has remained deferred rather than being quietly pulled back into scope

## Summary statement

Sprint 5 is the deliberate extraction sprint. `0.5.0` should optimize for the shortest credible path to a fully functional Calamum-owned integrated Samsung runtime at `0.6.0` with no required external Heimdall installation, even if that means the Sprint 5 boundary is structurally stronger than it is polished.
