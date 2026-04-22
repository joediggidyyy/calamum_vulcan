# Calamum Vulcan — `0.5.0` Detailed Planning

## Sprint shell document

**Release target:** `0.5.0`  
**Sprint position:** Sprint 5 of 6  
**Roadmap stage:** Stage III — Transport Autonomy  
**Sprint theme:** efficient integrated transport extraction  
**Current backend posture:** Sprint 4 carried Heimdall as a delegated lower transport. Sprint 5 collapses the external dependency.  
**Document purpose:** Define the detailed structural extraction contract for Sprint `0.5.0`, including `FS5-01` acceptable-disruption rules.

## FS5-01: Extraction Boundary and Acceptable-Disruption Contract

Sprint 5 prioritizes structural transport extraction over intermediate polish. To do this without creating false regression signals, `FS5-01` establishes the following acceptable-disruption rules:

1. **Extraction over Completeness (Temporary):** 
   - Heimdall features not required for the supported-path critical sequence can be temporarily degraded or disabled during extraction. 
   - Polishing error messages on edge cases is lower priority than owning the Samsung download-mode detection seam.

2. **Native Replacement Permitted:**
   - Any execution logic interacting with Samsung properties (detect, PIT parsing, execution handoffs) must push behind the `calamum-owned` boundary.
   - Using embedded Heimdall-derived logic is acceptable *only* if the external standalone execution requirement drops. The execution boundary must be ours.

3. **External Heimdall Demotion:**
   - `Heimdall` execution flags become explicit regression oracles.
   - Any runtime log must categorize Heimdall interactions defensively (e.g., `oracle_check`, `fallback_execution`) rather than primary transport.

4. **Testing Disruption Safety:**
   - Simulated environments (like `temp/fs_p05_scripted_simulation`) must pass based on the *Calamum-native* path.
   - Tests expecting the external Heimdall wrapper behavior will be rewritten to expect the new native seams. This is not semantic drift; it is the planned structural progression of Sprint 5.

This contract pins the sprint grammar so temporary incompleteness does not get mistaken for project drift.

## Workstream Blueprint

### Lane A: Detect and Identity
Replace external `heimdall detect` with native USB descriptor parsing for Samsung download-mode identification.

### Lane B: PIT Ownership
Absorb PIT acquisition and parsing. Ensure the system owns the mapping of partition strings to flash regions without relying on Heimdall's stdout format.

### Lane C: Write-path Seam
Execute flash plans with internal supervision. Replace subprocess polling of Heimdall with native transfer-state management or a deeply embedded, strongly-supervised Calamum layer.

### Lane D: Regression-Oracle Discipline
Keep Heimdall available as a parallel validator (where appropriate) but never as the critical dependency on the primary user path.

### Lane E: Package-only Closeout
Seal the evidence boundary without triggering a PyPI release (deferred to 1.0.0).