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

### Lane A: Detect and Identity (FS5-02 Execution Plan)
Replace external `heimdall detect` with native USB descriptor parsing for Samsung download-mode identification.
- **Execution Strategy:** Implement `pyusb` (a pure-Python wrapper around `libusb-1.0`). This guarantees cross-platform independence and avoids OS-specific workarounds (e.g., Windows WMI) mapping directly to how LOKE and Heimdall manage transport.
- **Future-proofing:** The USB scanner will use a generic vendor/product registry. While targeting Samsung Download Mode (VID `0x04E8`, PID `0x685D`) immediately, this structure lets us expand trivially to Google/Fastboot (VID `0x18D1`) and other Android boundaries later without rewriting the runtime base.
- **Diagnostic Honesty & Self-Resolution:** The scanner must explicitly trap OS-level USB access errors. Crucially, CodeSentinel principles mandate "no required user action" and "installs should be self-resolving." Rather than generating static Zadig UX instructions on failure, the application will provide a seamless backend remediation (e.g. self-installing WinUSB dependencies dynamically on Windows or pushing udev rules automatically with elevated permissions on Linux), resolving the error state and continuing the flash sequence without failing entirely.
- **Demotion:** The existing `BoundHeimdallWorker` polling step will be pushed to an explicit `oracle_check` fallback lane.

### Lane B: PIT Ownership
Absorb PIT acquisition and parsing. Ensure the system owns the mapping of partition strings to flash regions without relying on Heimdall's stdout format.

### Lane C: Write-path Seam
Execute flash plans with internal supervision. Replace subprocess polling of Heimdall with native transfer-state management or a deeply embedded, strongly-supervised Calamum layer.

### Lane D: Regression-Oracle Discipline
Keep Heimdall available as a parallel validator (where appropriate) but never as the critical dependency on the primary user path.

### Lane E: Package-only Closeout
Seal the evidence boundary without triggering a PyPI release (deferred to 1.0.0).

## Identified Gaps & Prerequisites
Before writing code for `FS5-02`, we must address the following implementation gaps:
1. **Dependency Addition:** We must update `pyproject.toml` to include `pyusb` for direct resolution upon installation.
2. **Backend Binary Distribution:** `pyusb` needs a `libusb-1.0.dll` backend. We *must* natively bundle this library inside our `.whl` distribution. Relying on user OS systems directly violates self-resolving installs.
3. **Testing Independence:** We need a mock `pyusb` device context so that CI and `pytest` sweeps do not fail or require real physical Samsung devices to test the `calamum_vulcan.usb` boundaries. 
4. **WinUSB Standalone Injector:** The prior plan of leaving USB drivers to user interaction (e.g. Zadig) is forbidden. CodeSentinel requires that the app resolves dependencies in real-time. We must integrate an automated WinUSB/libusbK injector for Windows deployments and automated udev configurations for Linux, handling elevation silently when necessary.