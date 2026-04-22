# Security Policy

**Document ID**: `CALAMUM_VULCAN_SECURITY`  
**Status**: Public vulnerability reporting  
**Owner**: ORACL-Prime  
**Project**: Calamum Vulcan  
**Last updated**: 2026-04-22

---

<p align="center">
  <img src="calamum_vulcan/assets/branding/polymath_global.png" alt="Polymath Global Logo" width="150">
</p>

## Scope

Calamum Vulcan is a Samsung-focused Android flashing platform with GUI-first workflows, package-aware preflight validation, and audit-ready evidence.

Security reports are especially valuable for:

- package or archive intake, manifest parsing, and checksum validation
- preflight or runtime-boundary bypasses
- evidence export, transcript retention, or local-path leakage
- credential handling in release or publication tooling
- subprocess, device-control, or packaging behavior that exceeds the documented support posture

If you are unsure whether something is security-relevant, report it privately first.

## Supported release lines

| Release line                      | Status                                                                   |
| --------------------------------- | ------------------------------------------------------------------------ |
| `main`                            | supported for coordinated disclosure                                     |
| latest tagged release boundary    | supported                                                                |
| older tags or ad hoc local builds | best effort; you may be asked to retest on the latest supported boundary |

The latest public package index release can lag behind the latest tagged repository boundary. Reports against either surface are still welcome.

## How to report a vulnerability

Please **do not open a public GitHub issue** for a sensitive vulnerability.

Preferred reporting path:

1. use GitHub private vulnerability reporting / a private security advisory for this repository if it is available in your view
2. if private reporting is not available, contact the maintainer privately through GitHub rather than posting details publicly

Please include:

- affected version, tag, or commit SHA
- host OS and Python version
- concise reproduction steps
- expected behavior versus actual behavior
- impact assessment
- minimal proof of concept or log excerpt, with sensitive values redacted

Please do **not** include real credentials, tokens, personal device identifiers, or proprietary firmware images unless the maintainer explicitly asks for them through a private channel.

## Coordinated disclosure expectations

Calamum Vulcan aims to:

- acknowledge a private report within 7 calendar days
- provide an initial triage or status update within 14 calendar days
- coordinate a fix and disclosure timeline based on severity, reproducibility, and release risk

When possible, please allow a private remediation window before public disclosure.

## Public issues are fine for

Public GitHub issues are appropriate for:

- non-sensitive hardening suggestions
- documentation gaps that do not reveal an exploit path
- already-public warning-tier findings that do not create an active exploitation risk

If there is any doubt, default to a private report first.

## Scope notes

A few practical guardrails for this repository:

- the Windows packaged workflow is the most empirically reviewed host surface today
- Linux, macOS, source-tree-only flows, and non-public live flashing behavior can still contain security bugs and are still in scope for private reporting
- packaging, publication, and evidence-export tooling are in scope because they affect distribution integrity and operator safety
