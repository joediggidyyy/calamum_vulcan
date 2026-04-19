# Calamum Vulcan — Samsung-Focused Open-Source Android Flashing Platform

## Research report and build plan

**Project context:** subordinate-repository research and build-planning artifact  
**Prepared for:** joediggidyyy  
**Date:** 2026-04-16

## Executive summary

The strongest path to an open-source Android flashing platform focused on Samsung devices is **not** to start from zero. The research supports a **staged Heimdall-replacement strategy**:

1. **Fork and stabilize Heimdall** as the initial Samsung transport baseline.
2. Add a **new safety-focused orchestration layer** for device detection, package validation, guided flashing, and structured logs.
3. Make the **desktop GUI mandatory** and treat it as a primary product differentiator rather than a thin wrapper over command-line actions.
4. Keep a **secondary scriptable CLI / automation surface** for testing, labs, and expert workflows.
5. **Gradually replace parts of Heimdall** in substantial sprint-sized layers until the platform reaches full runtime autonomy.
6. Expand later to support **fastboot** and **adb-assisted workflows** where appropriate, but keep Samsung download-mode flashing as the core design center.

This recommendation is driven by five facts from the research:

- Samsung flashing is historically centered on **Odin / Odin protocol / download mode**, not fastboot alone.
- **Heimdall already implements the Samsung low-level protocol** using `libusb`, is cross-platform, and exposes key operations like `flash`, `download-pit`, and `print-pit`.
- Heimdall also already models a **firmware package format** with device metadata, PIT references, and per-file partition mapping.
- Android’s official tooling (`fastboot`, Android Flash Tool, `adb`) provides good **workflow ideas** and testing patterns, but it is **not a Samsung-download-mode replacement**.
- The biggest real-world failure modes are **driver issues, wrong package/device combinations, PIT mismatches, bad cables/hubs, and opaque UX**, all of which are product/design problems more than protocol problems.

## Project framing

The project is to deliver a platform that is:

- open source
- Android flashing capable
- primarily aimed at Samsung devices
- desktop GUI mandatory
- practically buildable
- safer and easier to use than the current mix of leaked Odin binaries, scattered community instructions, and low-visibility tooling

The updated planning assumption for this project is:

- **Begin with the Heimdall core, then progressively replace it** for Samsung protocol transport.
- **Make the GUI mandatory** for the MVP and beyond.
- **Align the UI visual language with the CodeSentinel / Calamum operations aesthetic** shown in the provided references until further notice.
- **Use substantial sprint releases as the top-level implementation shells**, with each sprint mapped to a middle-version bump in `0.X.0`.
- **Target full Heimdall runtime autonomy at `0.6.0`**, then evaluate `1.0.0` only after post-autonomy hardening.

## Source-quality note

This report prioritizes:

1. **Primary or near-primary technical sources**: AOSP docs, Android Developers docs, Heimdall repo and platform readmes
2. **Secondary context**: Wikipedia for Odin background
3. **Community workflow evidence**: LineageOS install instructions using Heimdall

One recent Samsung claim surfaced through Wikipedia: that some 2026 Samsung devices may require **Maintenance mode** before download mode access. Because the linked Android Authority article could not be fetched from this environment, treat that item as an **emerging risk to validate on hardware**, not as a settled design fact.

## What exists today

### Flashing tool landscape

| Tool               | Ownership                                            | Main target                                    | Transport/mode                               | Strengths                                                                      | Limits for this product direction                                                               |
| ------------------ | ---------------------------------------------------- | ---------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| Odin               | Samsung / proprietary / leaked in public circulation | Samsung devices                                | Download mode / Odin protocol                | Widely known in Samsung community; supports Samsung firmware flows             | Not openly released, not open source, weak legal/product foundation for a credible OSS platform |
| Heimdall           | Open source (MIT)                                    | Samsung devices                                | Download mode / Odin 3 protocol via `libusb` | Cross-platform, existing code, package format, PIT tooling                     | Aging codebase, older UX, uneven device coverage, needs modernization                           |
| `fastboot`         | Official Android tooling                             | Pixel/Nexus and other fastboot-capable devices | Fastboot mode                                | Official, scriptable, well documented                                          | Not the primary Samsung flashing mechanism                                                      |
| Android Flash Tool | Official Google web tool                             | Pixel and a small set of supported boards      | WebUSB + adb/fastboot workflow               | Excellent guided UX inspiration                                                | Device scope is not Samsung-centered                                                            |
| `adb`              | Official Android tooling                             | General Android device communication           | Android system / debugging layer             | Great for detection, logs, device prep, reboot helpers, screenshots, scripting | Not a replacement for low-level Samsung firmware flashing                                       |

## Core research findings

### 1) Heimdall is the most relevant open-source foundation

Heimdall describes itself as a **cross-platform open-source tool suite used to flash firmware onto Samsung mobile devices**. Its README and Glass Echidna site both explain that Heimdall talks to **Loke** on the device using the Samsung-developed protocol often called the **Odin 3 protocol**, with USB handled by **`libusb`**.

This is the single most important architectural finding: the open-source path already has a working low-level Samsung transport model.

### 2) Heimdall’s repo already maps to a usable product architecture

The Heimdall repository is split into clean layers:

| Repo area                  | Role                                               |
| -------------------------- | -------------------------------------------------- |
| `libpit/`                  | PIT parsing and partition metadata support         |
| `heimdall/`                | CLI flashing engine and actions                    |
| `heimdall-frontend/`       | Qt GUI frontend                                    |
| `Linux/`, `OSX/`, `Win32/` | Platform install/build docs and packaging guidance |
| root `CMakeLists.txt`      | Top-level build orchestration                      |

The root CMake configuration adds `libpit`, `heimdall`, and optionally `heimdall-frontend`, which is a strong sign that the project already separates:

- transport + protocol logic
- PIT/partition metadata handling
- user-facing workflow/UI

That separation is exactly what a modern flashing platform should preserve.

### 3) Heimdall’s CLI actions reveal the right safety-critical primitives

The codebase exposes actions such as:

- `flash`
- `download-pit`
- `print-pit`
- device detection and info flows

These actions matter because a Samsung-safe product should not jump straight to “flash arbitrary files.” It should support this safer sequence:

1. detect device
2. identify product code/model
3. read or download PIT
4. compare package vs. device metadata
5. perform only the allowed flash plan
6. preserve logs and recovery guidance

The source also shows a useful detail: when a PIT file is supplied **without repartitioning**, Heimdall verifies the local PIT data against the device PIT. That is an important pattern for any new platform because it reduces catastrophic mismatch risk.

### 4) Heimdall already has a package spec worth learning from

The Windows and Linux readmes describe a **firmware package** that is basically:

- a `tar.gz`
- containing the flash files
- containing a required `firmware.xml`

That metadata includes:

- firmware name/version
- platform name/version
- developer info
- supported devices
- product codes
- PIT reference
- repartition flag
- no-reboot flag
- partition/file entries

This is a major design gift. Even if a new project does not reuse the exact XML format, it should keep the same high-value concepts:

- explicit device compatibility
- explicit partition mapping
- explicit PIT linkage
- explicit flash options
- reusable package artifacts

### 5) Windows driver handling is part of the product, not an edge case

Heimdall’s Windows instructions explicitly require replacing the Samsung USB composite device driver using **Zadig / WinUSB**. That means the Windows flashing experience is inseparable from driver state.

A new platform must therefore treat driver setup as a **first-class workflow** with:

- detection
- guided install/uninstall
- driver-state checks before flashing
- clear recovery instructions

### 6) Community workflows still rely on expert sequencing

The LineageOS instructions for the Galaxy S III use a simple but telling example:

- boot to download mode
- run `heimdall flash --RECOVERY recovery.img --no-reboot`
- manually reboot directly into recovery so stock firmware does not overwrite the custom recovery

This demonstrates that the platform needs workflow intelligence, not just raw flashing commands. A strong product must know when:

- `--no-reboot` is required
- an immediate reboot into recovery is required
- device-specific post-flash actions matter

### 7) AOSP tooling is useful as workflow inspiration, not as the Samsung transport backend

AOSP’s fastboot and Android Flash Tool docs provide several design ideas worth copying:

| AOSP idea                                        | Relevance to Samsung platform                   |
| ------------------------------------------------ | ----------------------------------------------- |
| explicit prerequisite checks                     | build preflight and environment validation      |
| device-mode instructions                         | guided entry into download mode / recovery mode |
| unlock / wipe / relock warnings                  | destructive-action confirmation UX              |
| USB troubleshooting guidance                     | same problem class exists for Samsung/Heimdall  |
| scripted device selection and command-line usage | valuable for CI, labs, and advanced users       |
| browser or GUI-based guided flashing             | good UX inspiration                             |

But these tools are largely centered on **fastboot-capable** hardware like Pixel/Nexus, while Samsung download-mode flashing requires Samsung-specific transport logic.

### 8) `adb` should be treated as a companion subsystem

Android Developers documentation shows that `adb`:

- is part of Platform Tools
- supports USB and Wi-Fi device communication
- can enumerate devices, run shell commands, move files, collect screenshots, and reset test devices

For a Samsung flashing platform, `adb` is valuable for:

- preflight device inspection when Android still boots
- collecting logs before/after flashing
- reboot helpers on supported devices
- post-flash validation and automation

The initial companion-control priority should be:

- `adb devices -l` detection for normal-boot operator visibility
- standard `adb reboot` handoffs for `bootloader`, `recovery`, `sideload`, and `sideload-auto-reboot`
- Samsung-targeted `download` reboot handling carried as a vendor-specific compatibility lane that is validated on hardware before it becomes a supported default promise
- `fastboot devices` detection for bootloader-side lab workflows and broader Android control-surface growth

It should **not** be the core Samsung flashing path, but it should absolutely be part of the platform architecture.

## Samsung-specific constraints and implications

### What makes Samsung harder than a generic Android flasher?

| Constraint                                          | Design implication                                                   |
| --------------------------------------------------- | -------------------------------------------------------------------- |
| proprietary Odin/Loke protocol family               | need a Samsung-specific backend                                      |
| device/product-code fragmentation by market/carrier | compatibility must key off product code, not just marketing name     |
| PIT-driven partition mapping                        | platform must read, store, compare, and validate PIT data            |
| different download mode entry methods               | device registry needs mode-entry instructions                        |
| Windows driver variability                          | installer/diagnostics must be built in                               |
| post-flash mode sequencing matters                  | workflow engine must encode model/package-specific steps             |
| cable/hub reliability is a real risk                | preflight and error guidance must be opinionated                     |
| emerging OEM restrictions may change access paths   | backend and device registry must be updateable without full rewrites |

## Recommended product direction

## Project name

The working product name is `Calamum Vulcan`.

Name intent:

- `Calamum` carries the calm, high-trust, operations-console posture already established in the visual direction
- `Vulcan` signals forge, tooling, and controlled heat appropriate to a flashing platform
- the combined name stays distinct from Samsung/Odin terminology while remaining memorable and product-grade

## Recommended architecture

### Strategic recommendation

**Use Heimdall as the initial transport base, but plan explicitly for staged replacement rather than permanent dependence.**

That gives the project:

- an existing Samsung protocol implementation to stand on immediately
- an MIT-licensed foundation
- bounded early reverse-engineering risk
- a credible GUI-first MVP sooner
- a clear path to full runtime autonomy without trying to solve every protocol problem at once

For clarity: the phrase "build around the Heimdall kernel" is interpreted here as **build around the Heimdall core/engine**, not as an operating-system kernel project.

### Chosen implementation posture

This document now treats **gradual replacement of Heimdall** as the primary implementation path.

That means the product is planned to evolve through three broad postures:

| Posture               | Meaning                                                                                              |
| --------------------- | ---------------------------------------------------------------------------------------------------- |
| wrapped dependence    | Heimdall performs the low-level work while the new platform owns UX, validation, and orchestration   |
| selective replacement | the new platform progressively takes over detection, PIT handling, sessions, and safe-path transport |
| runtime autonomy      | the supported device matrix no longer depends on Heimdall at runtime                                 |

## GUI mandate and CodeSentinel visual direction

The GUI is not optional. It is part of the product thesis.

### Updated UX position

| Surface          | Role                                         |
| ---------------- | -------------------------------------------- |
| Desktop GUI      | Mandatory primary surface for operators      |
| CLI              | Secondary expert / automation / CI surface   |
| Logs and reports | Shared evidence surface for both GUI and CLI |

The project should be framed as an **operations-grade flashing console**, not merely a command-line utility with a convenience frontend.

### Required GUI design goals

| Goal                       | Implication                                                                   |
| -------------------------- | ----------------------------------------------------------------------------- |
| high trust                 | the UI must communicate device state, package compatibility, and risk clearly |
| high signal density        | it should expose technical details without feeling cluttered                  |
| progressive disclosure     | novice-safe defaults with deeper expert controls behind explicit reveals      |
| destructive-action gravity | dangerous actions must feel materially different from routine actions         |
| operational clarity        | preflight, transfer, resume, recovery, and post-flash states must be obvious  |
| auditability               | every session should be exportable as a report or log bundle                  |

### CodeSentinel / Calamum style guidance

The provided references establish a visual contract that should be treated as the active design direction for this project.

#### Visual characteristics to carry forward

| Trait                | Guidance                                                             |
| -------------------- | -------------------------------------------------------------------- |
| overall mood         | dark, tactical, operations-console aesthetic                         |
| color base           | charcoal / graphite / near-black surfaces                            |
| lines and dividers   | thin, cool-toned separators and panel outlines                       |
| typography           | bold primary title with compact uppercase technical labels           |
| chart styling        | clean white or light-gray technical plotting over subdued grids      |
| accents              | restrained status accents in green, amber/orange, blue-gray, and red |
| destructive controls | large, unmistakable, high-contrast red action surfaces               |
| density              | information-rich dashboards with disciplined spacing                 |
| chrome               | minimal decorative noise; emphasis on signal and hierarchy           |
| brand treatment      | CodeSentinel / Calamum lockup and badge-style status indicators      |

#### Interaction patterns implied by the reference images

| Pattern                  | Recommendation                                                               |
| ------------------------ | ---------------------------------------------------------------------------- |
| command deck / side rail | keep a persistent right-side control deck for device and flash actions       |
| dashboard cards          | organize integrity, PIT, package, transport, and logs as independent modules |
| status pills             | use compact, color-coded pills for subsystem state and risk level            |
| telemetry surfaces       | use sparklines, histograms, radar/polygon summaries, and logs where useful   |
| terminal log pane        | retain a console-like live log area for technical trust and debugging        |
| big-action contrast      | separate dangerous buttons visually and spatially from normal controls       |

#### Design cleverness expectations

The cleverness should come from **workflow intelligence**, not ornament.

Recommended high-value GUI features:

- a **preflight board** that checks driver state, cable quality heuristics, battery guidance, device mode, and package compatibility before enabling flash
- a **device identity panel** that emphasizes product code over marketing name
- a **PIT explorer / PIT diff viewer** so the operator can inspect the active partition map before dangerous actions
- a **flash plan preview** that lists every partition, file, checksum result, and reboot consequence before execution
- a **resume-state visualizer** for `--no-reboot` / `--resume` workflows
- a **recovery guidance panel** that changes based on package metadata and device profile
- a **session evidence export** that captures logs, package metadata, PIT snapshot, and operator decisions

The design should feel like a calm, high-trust control room rather than a hobbyist ROM flashing toy.

### Architecture layers

| Layer                      | Responsibility                                                 | Initial implementation recommendation                                                                  |
| -------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Device transport backend   | low-level USB, sessions, flashing packets, PIT transfer        | Heimdall-derived C++ core at the start, progressively replaced across the sprint ladder using `libusb` |
| PIT and partition model    | PIT parsing, validation, partition metadata                    | reuse/modernize `libpit` concepts                                                                      |
| Flash orchestration engine | build flash plans, validate package vs. device, manage steps   | new service/library layer                                                                              |
| Package format             | structured metadata + files + checksums                        | evolve Heimdall package model; prefer JSON or YAML manifest over XML for new packages                  |
| Device registry            | product codes, aliases, entry instructions, known quirks       | versioned data registry in repo                                                                        |
| UX surfaces                | mandatory desktop GUI, secondary CLI, maybe local web UI later | start with GUI-first desktop app and retain CLI as expert support tooling                              |
| Diagnostics                | driver checks, USB checks, logs, report bundles                | built in from day one                                                                                  |

### Recommended initial feature set (MVP)

| Capability                                                 | Include in MVP? | Why                                                        |
| ---------------------------------------------------------- | --------------- | ---------------------------------------------------------- |
| detect Samsung device in download mode                     | Yes             | baseline requirement                                       |
| download PIT                                               | Yes             | essential for safe flashing                                |
| print/inspect PIT                                          | Yes             | essential for operator trust and validation                |
| product code compatibility check                           | Yes             | reduces accidental bricks                                  |
| flash a single vetted partition set (for example recovery) | Yes             | safer starting scope                                       |
| mandatory desktop GUI                                      | Yes             | explicit project requirement and major differentiator      |
| CodeSentinel-aligned visual system                         | Yes             | active branding and trust requirement                      |
| full repartition flow                                      | Not by default  | too risky for first release                                |
| package builder                                            | Yes, but simple | lets users distribute reproducible flash bundles           |
| Windows driver guidance                                    | Yes             | otherwise Windows users will fail early                    |
| structured logs / export report                            | Yes             | debugging and support are impossible without them          |
| `adb` preflight integration                                | Yes             | improves diagnostics, device detection, and reboot helpers |
| fastboot backend                                           | Later           | useful, but not central to Samsung-first scope             |
| browser/WebUSB flashing                                    | Later           | attractive UX, but not first milestone                     |

## Proposed package model

The new platform should keep Heimdall’s safety ideas but modernize the manifest.

### Suggested package fields

| Field                                 | Purpose                                   |
| ------------------------------------- | ----------------------------------------- |
| package name/version                  | human-readable release info               |
| supported manufacturer                | should be `Samsung` for first phase       |
| supported product codes               | authoritative compatibility list          |
| supported human-readable device names | convenience only                          |
| source firmware/build metadata        | traceability                              |
| PIT fingerprint or file               | partition compatibility anchor            |
| repartition allowed                   | explicit destructive-operation gate       |
| reboot policy                         | standard vs no-reboot                     |
| partition map                         | partition name/id to filename mapping     |
| file checksums                        | integrity validation                      |
| post-flash instructions               | immediate recovery boot, wipe steps, etc. |
| risk level                            | standard / advanced / destructive         |

## Complexity impact of accelerating beyond the staged replacement plan

This question depends on what "reverse engineer Heimdall" means. Because this document now adopts **gradual replacement** as the chosen plan, the most useful comparison is against that staged baseline.

### Case distinction

| Scenario                                                 | What it means                                                                                        | Relative complexity vs chosen staged-replacement plan |
| -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| understand and refactor Heimdall internals               | read the open-source code, isolate modules, modernize architecture inside the chosen roadmap         | about **1.0x**                                        |
| chosen staged replacement path                           | progressively absorb protocol responsibilities over multiple substantial releases                    | **baseline**                                          |
| compressed autonomy path                                 | try to replace most transport/session responsibilities much earlier than planned                     | about **1.5x to 2.0x**                                |
| fully independent Samsung backend from the outset        | reimplement transport, PIT handling, flash sequencing, and quirks without a staged dependence period | about **2.0x to 3.0x** for a serious MVP              |
| production-grade independent backend with broad coverage | own protocol implementation plus broad device support, driver tooling, testing, and safety hardening | about **3.0x to 5.0x+**                               |

### Why the increase is so large

The extra effort is not mostly in parsing files or drawing screens. It is concentrated in the hard-to-fake parts:

| Complexity source               | Why it grows sharply                                                               |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| Samsung protocol behavior       | low-level session and packet behavior must be rediscovered, verified, and hardened |
| PIT semantics                   | partition metadata and mismatch handling are safety-critical                       |
| device quirks                   | model/region differences create long-tail failure cases                            |
| resume/no-reboot state handling | these flows are subtle and easy to get wrong                                       |
| USB edge cases                  | timeouts, driver state, reconnects, and host differences multiply debugging effort |
| Windows support                 | WinUSB/Zadig and driver diagnostics become a major lane of work                    |
| confidence burden               | a new backend needs far more hardware validation before it becomes trustworthy     |

### Practical project recommendation

For this project, replacing Heimdall wholesale too early would still be a **major complexity and schedule increase** with relatively weak upside in the first version.

The better move is:

- adopt the staged replacement plan as the official path
- innovate heavily in the **GUI**, **package safety**, **device registry**, **preflight intelligence**, and **operator workflow** from Sprint 1 onward
- reduce Heimdall dependency sprint by sprint rather than treating it as either permanent or immediately disposable

### Bottom-line estimate

If the chosen staged-replacement path is treated as **1.0x baseline complexity**, then:

- **Chosen staged replacement path:** **1.0x**
- **Compressed early-autonomy plan:** roughly **1.5x to 2.0x**
- **Ground-up independent Samsung backend:** roughly **2.0x to 3.0x** for a serious MVP

In plain English: the staged path is difficult but tractable; trying to force early total autonomy turns a demanding platform project into a materially riskier protocol-reimplementation project.

## Safety model

The platform should adopt “safe by default, scary on purpose.”

### Hard safety rules

1. **Do not flash if product code is unknown or mismatched.**
2. **Do not repartition unless the package explicitly allows it and the operator confirms it.**
3. **Require PIT acquisition before any advanced flash plan.**
4. **Require checksums for every package payload.**
5. **Warn about battery, cable, and hub quality before starting.**
6. **Persist a machine-readable operation log for every run.**
7. **Block or heavily gate bootloader/critical partition flashes in MVP.**
8. **Treat recovery-mode immediate reboot requirements as package-defined workflow steps.**

### Suggested flash workflow

| Step | Description                                           |
| ---- | ----------------------------------------------------- |
| 1    | detect connected device / mode                        |
| 2    | retrieve product code and PIT if possible             |
| 3    | validate package metadata against device registry     |
| 4    | validate files and checksums                          |
| 5    | show exact flash plan to user                         |
| 6    | require explicit confirmation for destructive actions |
| 7    | execute with progress, logs, and error capture        |
| 8    | show next required reboot or recovery instructions    |
| 9    | collect post-flash status and save report             |

## Package-security and operator-override posture

This platform is intended for legitimate but deliberately customizable Android work. The security model therefore prioritizes **package-intake integrity**, **execution-path integrity**, and **operator-visible risk classification** over hiding device or package truth from the person operating the tool.

### Operating stance

- device identity, product code, mode, and package metadata remain visible by default in the operator surface
- rooted, custom-kernel, patched-vbmeta, or otherwise modified packages may be intentional lab inputs rather than automatic rejection cases
- the platform should surface suspicious traits clearly, keep the final flash plan explicit, and preserve expert override where the package is structurally sound
- the platform should hard-block only the conditions that make package intake or execution-path state untrustworthy

### What the platform should prove directly

| Security proof target                    | Practical meaning                                                                         |
| ---------------------------------------- | ----------------------------------------------------------------------------------------- |
| package bytes match reviewed digests     | the payload files going into the flash plan are the exact files that were reviewed        |
| archive layout is safe                   | package intake rejects traversal, absolute paths, link abuse, and duplicate conflicts     |
| flash plan matches the analyzed snapshot | execution uses the reviewed partition map and payload set rather than ad hoc inputs       |
| suspicious Android traits are visible    | rooted and tampered indicators are surfaced before execution rather than discovered later |
| execution gating stays sealed            | the operator cannot start flashing outside the platform-owned ready path                  |

### Operator-judgment territory

| Judgment surface                              | Why the operator still matters                                                            |
| --------------------------------------------- | ----------------------------------------------------------------------------------------- |
| novel custom kernel or recovery intent        | a custom image can be purposeful lab work or hostile modification                         |
| unusual but structurally valid partition plan | some expert workflows are legitimate even when they exceed a conservative default posture |
| provenance confidence for unsigned bundles    | integrity can be proven even when origin trust remains a human policy decision            |

### Security decision classes

| Decision class     | Meaning                                                                                            | Representative cases                                                                                                                                                             |
| ------------------ | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| hard block         | intake or execution-path trust is broken and the platform must stop                                | malformed manifest, missing payload, archive traversal, digest mismatch, reviewed package changed after analysis, flash request outside `READY_TO_EXECUTE`                       |
| bypassable warning | package is structurally usable but carries visible risk that the operator may intentionally accept | Magisk or `su` indicators, `test-keys`, insecure default props, AVB or dm-verity disablement, permissive SELinux, repartition request, unusual partition set, unknown provenance |

### Security implementation priorities for the next release boundary

| Priority                         | Why it matters                                                                                      |
| -------------------------------- | --------------------------------------------------------------------------------------------------- |
| safe archive intake boundary     | blocks traversal, absolute paths, link abuse, duplicate collisions, and size-trap package layouts   |
| real SHA-256 digest verification | ties manifest truth to actual payload bytes rather than placeholders                                |
| sealed analyzed-package snapshot | prevents time-of-check/time-of-use drift between review and execution                               |
| Android image heuristics         | surfaces root and tamper indicators without pretending every custom image is hostile                |
| adversarial parser testing       | hardens package import, manifest parsing, and backend-output normalization against malformed inputs |

## Sprint roadmap to full Heimdall autonomy

This first pass defines only the **outer sprint shells**. Each sprint is intentionally substantial and maps to a middle-version bump in the release line. The inward expansion into frame stacks comes later.

### Versioning rule for sprint boundaries

- Each sprint completion bumps **X** in `0.X.0`.
- Patch releases (`0.X.Y`) are reserved for stabilization inside a sprint boundary, not for redefining the sprint itself.
- The sprint ladder therefore targets:
  - `0.1.0`
  - `0.2.0`
  - `0.3.0`
  - `0.4.0`
  - `0.5.0`
  - `0.6.0`
- **Full Heimdall runtime autonomy is targeted at `0.6.0`.**
- `1.0.0` is intentionally **not** a sprint boundary; it is reserved for the post-autonomy stabilization and confidence milestone.

### Stage grouping

| Stage                            | Sprint range | Release range      | Purpose                                                                                   | Dependency posture                                                                  |
| -------------------------------- | ------------ | ------------------ | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| Stage I — Controlled Dependence  | Sprints 1-2  | `0.1.0` to `0.2.0` | establish the GUI-first product shell, safety model, and orchestration authority          | Heimdall still performs the critical runtime transport work                         |
| Stage II — Structural Extraction | Sprints 3-4  | `0.3.0` to `0.4.0` | absorb read-side and session-layer responsibilities into the new platform                 | Heimdall dependency narrows to selective transport fallback                         |
| Stage III — Transport Autonomy   | Sprints 5-6  | `0.5.0` to `0.6.0` | replace live flash responsibilities on the supported matrix and retire runtime dependence | Heimdall is reduced to fallback/reference, then removed from supported-path runtime |

### Sprint ladder

| Sprint   | Release target | High-level theme                             | What changes at this boundary                                                                                                                                                      | Heimdall posture after sprint         |
| -------- | -------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Sprint 1 | `0.1.0`        | GUI-first product shell                      | the platform becomes a real operations console with mandatory GUI, package awareness, preflight model, and structured logging while Heimdall remains the transport executor        | full wrapped dependence               |
| Sprint 2 | `0.2.0`        | orchestration ownership                      | the new platform owns flash plans, device registry, package validation, recovery guidance, and operational state even though Heimdall still executes the low-level transport paths | controlled adapter dependence         |
| Sprint 3 | `0.3.0`        | read-side autonomy                           | detection, info, PIT inspection/download logic, and non-destructive inspection flows begin moving into the native platform for the supported device subset                         | partial runtime dependence            |
| Sprint 4 | `0.4.0`        | session and safe-path extraction             | the platform takes ownership of more session-layer and safe-path transport responsibilities, shrinking Heimdall to narrower fallback lanes                                         | selective fallback dependence         |
| Sprint 5 | `0.5.0`        | default native transport on supported matrix | the native backend becomes the default path for standard supported flashing lanes, while Heimdall remains available only for edge, legacy, or not-yet-migrated cases               | optional fallback only                |
| Sprint 6 | `0.6.0`        | full Heimdall autonomy                       | the supported device matrix no longer requires Heimdall at runtime; Heimdall is retained only as historical reference, migration aid, and regression oracle                        | autonomous on supported runtime paths |

### Autonomy gate at `0.6.0`

The project should not claim full Heimdall autonomy until all of the following are true for the supported matrix:

- the runtime does not shell out to or dynamically depend on Heimdall for normal operations
- the platform owns device detection and identity handling
- the platform owns PIT retrieval / parsing / comparison flows
- the platform owns flash planning and operator safety validation
- the platform owns live transfer state, progress, resume/no-reboot handling, and reporting
- Heimdall remains only as a reference implementation, migration comparison tool, or regression fixture source

### What this pass does not do yet

This pass intentionally does **not** decompose the sprints into frame stacks, engineering sublanes, or implementation frames. It only defines the major sprint shells and the release ladder to full autonomy.

The detailed companion shell for Sprint 1 now lives in:

- `Samsung_Android_Flashing_Platform_0.1.0_Detailed_Planning.md`

## Suggested implementation stack

### Lowest-risk stack

| Layer                    | Recommendation                                                                                                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------ |
| low-level backend        | C++ Samsung backend, Heimdall-derived at first and progressively replaced across the sprint ladder, using `libusb` |
| partition parsing        | modernized `libpit` or successor                                                                                   |
| package/validation layer | same repo, typed library API                                                                                       |
| GUI                      | **Qt 6 desktop app mandatory**; dashboard-first shell aligned to CodeSentinel / Calamum styling                    |
| CLI                      | native secondary expert / automation surface                                                                       |
| logs / reports           | JSON + human-readable Markdown/text exports                                                                        |

### Why this stack

- It preserves the only clearly relevant open-source Samsung transport base found in the research.
- It minimizes protocol reimplementation risk.
- It keeps Windows/Linux support realistic.
- It allows gradual replacement of old UI/process-launch behavior.

### Alternative stack

A longer-term redesign could move the orchestration layer to **Rust** while keeping the initial Heimdall transport as an external backend or FFI dependency. That is attractive for safety and packaging, but it is a second-stage move, not the fastest route to a working early prototype.

## `0.1.0` subordinate-repository and PyPI packaging checklist

This project will initially publish as a **public subordinate repository nested inside a broader superproject** and then as a **PyPI-distributed package**. This `0.1.0` posture preserves surrounding project context while making the nested release root the only public package boundary.

For this packaging milestone:

- **unit tests are necessary but insufficient**
- **scripted simulation testing is mandatory**
- **empirical testing is mandatory**
- **PyPI publication should happen only after a TestPyPI-style dress rehearsal succeeds**

### Packaging boundary assumptions

Before publication, the team should treat the nested release root as the authoritative public repo root even while it remains nested inside a broader superproject.

That means the publishable repo should expose only the surfaces that a public user needs:

- the Python package itself
- packaging/build metadata
- public documentation
- tests and scripted simulation runners that are safe to share
- license and release notes
- release automation surfaces that operate entirely from the nested repo root

For `0.1.0`, the parent repo may retain broader planning and operational context, but every build, install, test, release, and publication action must succeed from the nested repo root without reaching upward into parent-only files.

Creating the public GitHub repository **now** is appropriate under this plan. It should be treated as an **early boundary-locking move** inside the publication lane: create the public repo shell and wire the nested repo remote early, then use the later publication stacks to prove that the repo is genuinely ready for public consumption and PyPI release.

The public repo seed now exists at:

- `https://github.com/joediggidyyy/calamum_vulcan`

Observed seed status on 2026-04-18:

- visibility: public
- default branch: `main`
- current seed content: initial MIT `LICENSE`
- releases: none published yet

That means `FS-P01` no longer needs to decide whether a public repo should exist; it now needs to attach the nested release root to the existing public seed and harden that boundary for real release work.

### Release checklist

#### 1) Subordinate repository boundary and public-surface audit

- [ ] Treat the nested release root as the authoritative public repo root for `0.1.0` and verify imports, builds, and tests succeed from that root alone.
- [ ] Confirm the repository/package/import naming contract is consistent enough for public use (`calamum_vulcan` should not depend on a different hidden package identity unless explicitly justified).
- [ ] Confirm every public-user-facing artifact required for publication lives inside the nested repo rather than depending on parent-repo copies.
- [ ] Remove workspace-only or machine-local references from public-facing docs, examples, and scripts.
- [ ] Remove stale interpreter guidance that points public users to development-only environments when the nested repo should default to the validated public runtime.
- [ ] Exclude temporary artifacts, local exports, and parent-repo-only evidence bundles from the subordinate repo publication surface.

#### 2) Packaging metadata and build contract

- [ ] Add a subordinate-repo-local `pyproject.toml` with explicit build backend, dependency metadata, classifiers, URLs, and entry points.
- [ ] Set `version = 0.1.0` consistently across package metadata, user-facing docs, and release notes.
- [ ] Declare `requires-python` narrowly enough to match the versions actually validated for the release.
- [ ] Confirm runtime dependencies are separated cleanly from development/test-only dependencies.
- [ ] Confirm GUI launch entry points and any CLI console scripts are declared explicitly and work from an installed wheel.
- [ ] Build both `sdist` and `wheel` artifacts successfully from the nested repo root.
- [ ] Verify the long description renders correctly and safely for PyPI.
- [ ] Confirm packaging commands and CI entry points use the nested repo root as the working directory.

#### 3) Public API and artifact sanity checks

- [ ] Verify that importing `calamum_vulcan` does not trigger GUI startup, local-path assumptions, or heavy side effects.
- [ ] Verify the package exposes only intended public modules and symbols and does not leak workspace-only helpers accidentally.
- [ ] Verify packaged data files, fixtures, manifests, and static assets are included intentionally rather than accidentally omitted or over-included.
- [ ] Verify the package can generate reports, fixtures, and simulation artifacts from an installed environment, not only from the source tree.
- [ ] Verify that no runtime or test helper climbs above the subordinate repo root through relative parent-path assumptions.

#### 4) Automated test baseline beyond build success

- [ ] Run the full Python test suite from the subordinate repo root and record the exact interpreter and platform matrix used.
- [ ] Keep the existing `pytest`/`unittest` logic suite as the baseline gate for state, preflight, package, reporting, adapter, and integration coverage.
- [ ] Add install-smoke automation that creates a clean environment, installs the built wheel, imports the package, and exercises the main entry points.
- [ ] Add CLI-smoke automation that verifies help text, evidence export, and the integrated release-close bundle from an installed artifact rather than from the source checkout.
- [ ] Add artifact-integrity checks that confirm wheel contents, packaged manifests, and required metadata files match expectations.
- [ ] Add a subordinate-repo-local runner or task surface that reproduces the publication gate consistently.

#### 5) Scripted simulation testing (mandatory)

Scripted simulation testing is the first release gate **beyond unit tests**. It should prove that the packaged product behaves correctly across the major non-live operational scenarios.

- [ ] Run a scripted scenario matrix covering at minimum: no-device, ready, blocked, mismatched package, transport failure, and resume-handoff paths.
- [ ] Run the integrated release-close suite (for example the current `--integration-suite sprint-close` flow) from the subordinate repo root and archive the resulting bundle artifacts.
- [ ] Run offscreen GUI launch scripts for representative happy-path and blocked-path flows in the publishable environment.
- [ ] Script validation of JSON and Markdown evidence export outputs and confirm their schemas and sections remain stable.
- [ ] Script wheel-install simulations on every supported host OS in scope for `0.1.0`.
- [ ] Script failure-mode simulations for missing package metadata, incompatible product codes, and adapter-backed transport failure.
- [ ] Script report and bundle generation checks so release artifacts can be reproduced deterministically by CI or a release engineer.

#### 6) Empirical testing (mandatory)

Empirical testing is the second release gate **beyond scripted simulation**. It should prove that the product is understandable, installable, and operationally trustworthy for a human operator in realistic conditions.

- [ ] Perform a clean-machine or clean-environment install test from the artifacts produced by the nested repo and verify the documented quickstart actually works.
- [ ] Perform a visible GUI review, not only an offscreen run, to confirm layout density, destructive-action contrast, and evidence readability in the packaged build.
- [ ] Manually review the no-device, incompatible-package, and transport-failure flows to confirm the operator guidance reads clearly and does not rely on internal jargon.
- [ ] Manually inspect the exported evidence bundle for completeness, readability, and public-safe wording.
- [ ] Perform sacrificial-device-only empirical testing for any live flashing behavior that is claimed in the `0.1.0` package.
- [ ] If live-device claims remain out of scope for package publication, explicitly state that the published release is simulation-validated.
- [ ] Perform a Windows driver and USB readiness review in the packaged environment without relying on parent-repo knowledge.
- [ ] Perform at least one recovery-guidance review for no-reboot and resume instructions to confirm the operator can follow the packaged workflow without source-code context.

#### 7) Cross-platform and runtime matrix checks

- [ ] Validate the package on Windows first, because that is the highest-priority host surface for Samsung flashing workflows.
- [ ] Validate the package on Linux for the same artifact set if Linux is listed as supported for `0.1.0` publication.
- [ ] Record whether macOS is unsupported, deferred, or experimentally supported rather than leaving that status ambiguous on PyPI.
- [ ] Confirm the packaged release uses the intended public runtime environment and does not silently depend on a development-only interpreter layout.
- [ ] Confirm the published wheel tags and runtime claims match the validated interpreter matrix.

#### 8) Release documentation and support readiness

- [ ] Add a public release checklist or quickstart in the subordinate repo that tells users how to install, launch, run simulations, and export evidence.
- [ ] Document the supported host matrix, known limitations, and explicit non-goals for the published `0.1.0` package.
- [ ] Document that live flashing safety requires sacrificial-device discipline and that unsupported device behavior is outside the published support boundary.
- [ ] Document the known Qt packaging and font warning situation if it remains unresolved at release time.
- [ ] Add a concise troubleshooting section for install failures, GUI launch failures, and missing dependency or runtime issues.
- [ ] Ensure release notes and changelog surfaces can stand on their own when viewed outside the parent repo.

#### 9) TestPyPI and publication rehearsal

- [ ] Publish the candidate release from the subordinate repo to a rehearsal target such as TestPyPI before any real PyPI publication.
- [ ] Install from the rehearsal registry into a clean environment and rerun the core scripted simulation suite.
- [ ] Verify that the published metadata, README rendering, wheel tags, and dependency resolution all match expectations.
- [ ] Verify that the package can be uninstalled and reinstalled cleanly.
- [ ] Verify that the release tag, artifact names, and validation evidence all point to the same nested-repo `0.1.0` boundary.

#### 10) Final publication gate

- [ ] Publish only after source-tree, nested-repo-root, and installed-artifact tests all pass.
- [ ] Publish only after scripted simulation coverage is complete for the main happy, blocked, mismatch, failure, and resume paths.
- [ ] Publish only after empirical validation matches the exact claims made in the public documentation.
- [ ] Publish only after public guidance is free of parent-repo path leakage and local-machine assumptions.
- [ ] Publish only after the release notes, version tags, artifacts, and validation evidence all point to the same `0.1.0` package boundary.

### Minimum evidence expected before PyPI publication

At minimum, the package publication decision for `0.1.0` should be backed by:

- a passing automated logic-test suite from the subordinate repo root
- a stack-archived shared security validation result for the publication lane with no blocking findings
- a passing scripted simulation suite from the packaged artifact context
- a recorded empirical install and GUI review
- a documented host and runtime matrix
- a TestPyPI rehearsal result
- a short known-limitations list and public support posture
- a release-root self-sufficiency check that proves the nested repo does not depend on parent-only files

## `0.1.0` publication frame stack

This publication lane should be executed from the nested repo root as the release root while the surrounding superproject remains external context. The parent repo may keep broader planning and operational context, but every stack in this lane must prove that the nested repo is independently publishable.

Every publication stack in this lane now closes through its stack-specific runner plus the shared security validation suite. Blocking findings fail the stack immediately; warning-tier findings remain visible in the archived evidence and must be carried forward explicitly.

### Ordered stack summary

| Stack    | Focus                                               | Estimated push size | Why it is its own stop point                                                                         |
| -------- | --------------------------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------- |
| `FS-P01` | subordinate-repo boundary and release-root contract | 1.0 to 1.5 hours    | locks the public boundary before build, docs, and automation start drifting across parent-repo edges |
| `FS-P02` | packaging metadata and build artifact contract      | 1.0 to 2.0 hours    | proves the nested repo can produce valid installable artifacts from its own root                     |
| `FS-P03` | installed-artifact and public API smoke lane        | 1.0 to 2.0 hours    | verifies the package works after installation, not only inside the source tree                       |
| `FS-P04` | scripted simulation and reproducibility lane        | 1.0 to 2.0 hours    | closes the non-live operational validation gap beyond ordinary unit tests                            |
| `FS-P05` | empirical review and public-doc readiness           | 1.0 to 2.0 hours    | aligns human-facing guidance, GUI behavior, and public support claims                                |
| `FS-P06` | TestPyPI rehearsal and publication gate             | 1.0 to 1.5 hours    | consolidates the release evidence and gives `0.1.0` one clean go/no-go boundary                      |

### Why 6 stacks is the right cut

The publication lane has six different kinds of proof to produce: boundary discipline, build correctness, installed-artifact behavior, scripted simulation, empirical review, and registry rehearsal. Keeping each proof type in its own stack preserves clean stop points and makes it easier to tell whether a failure belongs to packaging, validation, or publication readiness.

## `FS-P01` — Subordinate-repo boundary and release-root contract

**Target outcome:** the nested release root is treated as the authoritative `0.1.0` public repo root and no required publication surface depends on parent-only files.

**Primary validation gate:** release-root audit passes and the nested repo contains every public-facing artifact needed for build, install, docs, and validation.

| Frame | Push                                                                                                                                                                                      | Natural rest point                                                                       |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| 1     | declare the `0.1.0` nested-repo publication posture, release root, and evidence locations                                                                                                 | the boundary contract is pinned in writing                                               |
| 2     | inventory every artifact the public repo must own directly and lock the public repo name, visibility, and remote contract                                                                 | required publication surfaces and repo identity are explicit                             |
| 3     | attach the nested repo to the existing public seed, reconcile the seed shell, and confirm release automation can target that repo from the nested root                                    | the public repo exists early without pretending the release is already publication-ready |
| 4     | remove or replace parent-repo path assumptions, stale interpreter guidance, and parent-only references in user-facing material while tightening ignore rules and release-root scaffolding | the nested repo behaves like a self-contained public surface                             |
| 5     | run a release-root audit and record any missing or overexposed surfaces before build work begins                                                                                          | the lane can proceed without boundary ambiguity                                          |

## `FS-P02` — Packaging metadata and build artifact contract

**Target outcome:** the nested repo can produce correct `sdist` and `wheel` artifacts with coherent metadata directly from the release root.

**Primary validation gate:** build artifacts complete successfully, package metadata is internally consistent, the rendered long description is publication-ready, and the shared security validation suite reports no blocking findings.

| Frame | Push                                                                                                               | Natural rest point                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| 1     | pin build backend, version, `requires-python`, dependency groups, classifiers, URLs, and entry points              | publication metadata is explicit rather than implied                     |
| 2     | define package-data inclusion rules for fixtures, manifests, static assets, and documentation-linked artifacts     | artifact boundaries are encoded in configuration                         |
| 3     | add a nested-repo-local build runner or task surface for repeatable artifact creation                              | build execution becomes reproducible                                     |
| 4     | review README rendering, changelog or release-note linkage, license visibility, and PyPI-facing description safety | public metadata reads cleanly before upload                              |
| 5     | build the candidate `sdist` and `wheel` and inspect their contents against the checklist                           | artifact production is trustworthy enough for installed-artifact testing |

## `FS-P03` — Installed-artifact and public API smoke lane

**Target outcome:** the built package behaves correctly outside the source tree and exposes only the intended public surface.

**Primary validation gate:** clean-environment install-smoke, import-smoke, CLI-smoke, artifact-integrity checks, and the shared security validation suite all pass without blocking findings.

| Frame | Push                                                                                                                          | Natural rest point                                                 |
| ----- | ----------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| 1     | freeze the installed-artifact validation matrix, including supported interpreters, host OS priorities, and smoke expectations | installed-context proof is scoped tightly enough to automate       |
| 2     | create a clean-environment install and import runner for the built wheel                                                      | basic install viability is testable                                |
| 3     | add CLI smoke coverage for help text, evidence export, and the release-close integration bundle                               | the public command surface is exercised from an installed artifact |
| 4     | add artifact-integrity checks for packaged manifests, fixtures, metadata files, and static assets                             | package contents become auditable rather than assumed              |
| 5     | run the installed-artifact validation bundle and log any source-tree leakage or public-API surprises                          | the package is trustworthy enough for deeper simulation work       |

## `FS-P04` — Scripted simulation and reproducibility lane

**Target outcome:** the packaged product proves its non-live operational scenarios reproducibly from publication-safe surfaces.

**Primary validation gate:** scenario matrix automation, integration-bundle generation, deterministic report outputs, and the shared security validation suite all pass without blocking findings.

| Frame | Push                                                                                                                        | Natural rest point                                       |
| ----- | --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| 1     | freeze the scripted scenario matrix and expected outputs for no-device, ready, blocked, mismatch, failure, and resume flows | simulation coverage is explicit                          |
| 2     | wire subordinate-repo-root and installed-artifact runners for the scenario matrix                                           | simulation execution is portable across release contexts |
| 3     | add offscreen GUI launch validation plus JSON and Markdown evidence-export checks                                           | shell behavior and evidence output are both covered      |
| 4     | tighten deterministic bundle and report assertions so CI and release engineers can reproduce the same artifacts reliably    | reproducibility becomes measurable                       |
| 5     | run the full scripted simulation suite and archive the resulting bundle evidence                                            | the release has a credible non-live validation story     |

## `FS-P05` — Empirical review and public-doc readiness

**Target outcome:** the human-facing release surface is understandable, supportable, and aligned with the actual package behavior.

**Primary validation gate:** clean-environment walkthroughs, visible GUI review, public-doc claim review, and the shared security validation suite all complete with aligned evidence and no blocking findings.

| Frame | Push                                                                                                                                 | Natural rest point                                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| 1     | review quickstart, troubleshooting, support posture, and release notes against the real nested-repo commands and artifacts           | documentation aligns with actual operator steps                   |
| 2     | perform a clean-environment install and quickstart walkthrough from the built artifacts                                              | install guidance is empirically verified                          |
| 3     | run a visible GUI review for layout density, destructive-action contrast, trust cues, and evidence readability                       | the operator-facing shell is reviewed as a public product surface |
| 4     | inspect exported evidence bundles and recovery guidance for completeness, readability, and public-safe wording                       | the support surface becomes human-usable                          |
| 5     | record known limitations, host-support posture, and the exact boundary between simulation-validated and live-device-validated claims | the release claims become honest and durable                      |

## `FS-P06` — TestPyPI rehearsal and publication gate

**Target outcome:** the `0.1.0` release candidate is rehearsed end to end and has one clean publication decision boundary.

**Primary validation gate:** the shared security validation suite reports no blocking findings, TestPyPI install and reinstall succeed when credentials are present, rehearsal metadata matches expectations, and the final publication checklist is fully satisfied.

| Frame | Push                                                                                                                   | Natural rest point                                                |
| ----- | ---------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1     | publish the rehearsal candidate from the nested repo and capture artifact identifiers, hashes, and version tags        | registry rehearsal begins from the correct root                   |
| 2     | install from the rehearsal registry into a clean environment and rerun the core scripted simulation bundle             | registry-delivered artifacts are validated, not just local builds |
| 3     | verify README rendering, wheel tags, dependency resolution, uninstall and reinstall behavior, and metadata correctness | distribution surfaces are proven coherent                         |
| 4     | reconcile any remaining checklist debt and align release notes, tags, artifacts, and evidence references               | every release surface points to the same boundary                 |
| 5     | assemble the final evidence pack and make the `0.1.0` go or no-go call                                                 | publication can proceed without ambiguity                         |

## `0.1.0` closeout checklist

This is the final release-close checklist for `0.1.0`.

When every open checkbox below is complete, the nested repo has fully closed the `0.1.0` boundary and the next active lane can move to `0.2.0` planning and execution.

### Current closeout state

| Surface | Current state | Evidence anchor |
| ------- | ------------- | --------------- |
| publication rehearsal | `FS-P06` completed with `publication_decision="go"` | `temp/fs_p06_testpypi_rehearsal/testpypi_rehearsal_summary.json` |
| release branch | `origin/main` now contains the sealed `0.1.0` closeout commit `d11a4ace26027aba944f03e61c63c3350477a0f7` | `git rev-parse HEAD`, `git push origin main` result from 2026-04-19 |
| release working tree | the final release tree was sealed into commit `d11a4ac` before post-closeout documentation updates reopened the local working tree | closeout commit output from 2026-04-19 |
| tag boundary | annotated tag `v0.1.0` now exists locally and on `origin` at `d11a4ace26027aba944f03e61c63c3350477a0f7` | `git push origin v0.1.0` result from 2026-04-19 |
| GitHub release object | still not created because the local GitHub auth surfaces failed during closeout (`gh` keyring token invalid and browser session unauthenticated) | `gh auth status`, GitHub release browser sign-in redirect from 2026-04-19 |
| PyPI production publication | still not published because the configured project-scoped API token is invalid for project `calamum-vulcan` | real PyPI upload attempt from 2026-04-19 |

### Already satisfied

- [x] `FS-P01` through `FS-P06` completed with archived execution evidence.
- [x] automated logic, installed-artifact, scripted-simulation, empirical-review, and shared security-validation gates all reached a green rehearsal posture for the `0.1.0` artifact set.
- [x] TestPyPI upload, registry-delivered install validation, uninstall/reinstall validation, and the final rehearsal publication decision all reached `go`.

### Remaining closeout actions

#### 1) Freeze the final `0.1.0` release tree

- [x] Review the current dirty working tree in the nested release root and decide exactly which pending files belong inside the final `0.1.0` boundary.
- [x] If any artifact-producing surface changed after the green `FS-P06` rehearsal, rerun the affected release runners and refresh the artifact hashes before sealing the boundary.
- [x] Confirm the final public docs, changelog language, and evidence references all still point to the same `0.1.0` artifact set.

#### 2) Seal the git release boundary

- [x] Create the final `0.1.0` release commit from the nested repo root.
- [x] Push `main` so `origin/main` contains the exact closeout commit.
- [x] Create an annotated git tag `v0.1.0` at the sealed release commit.
- [x] Push the tag and verify the tag, commit SHA, artifact hashes, and release evidence all resolve to the same boundary.

#### 3) Publish the public release surfaces

- [ ] Create the GitHub release for `v0.1.0` from the sealed tag with the final release notes and support posture. Current blocker: the local GitHub CLI keyring token is invalid and the browser session is not authenticated.
- [ ] Publish the `0.1.0` wheel and source distribution to the real PyPI project boundary, not only TestPyPI. Current blocker: the configured project-scoped PyPI API token is not valid for `calamum-vulcan`.
- [ ] Install the real PyPI release into a clean environment and rerun the core installed-artifact checks: help, ready describe-only review, evidence export, sprint-close bundle, uninstall, and reinstall.
- [ ] Record the final public URLs for the GitHub release and PyPI project page in the closeout evidence.

#### 4) Capture the final closeout evidence pack

- [ ] Update the `0.1.0` execution evidence surface with the final release-admin proof set: closeout commit SHA, `v0.1.0` tag, GitHub release URL, PyPI URL, and the date of the final production publication validation.
- [ ] Confirm the final artifact hashes, version strings, release notes, and public metadata all point to the same `0.1.0` boundary.
- [ ] Mark the `0.1.0` publication lane as fully closed in the active authority surfaces.

#### 5) Activate the `0.2.0` lane cleanly

- [ ] Open the `0.2.0` planning surface and make it the next active execution lane only after the `0.1.0` closeout evidence is complete.
- [ ] Carry the verified `0.1.0` follow-on debt into the `0.2.0` backlog: real checksum verification, safe real-package importer, sealed analyzed-package snapshot, Android-image suspiciousness heuristics, Qt deployment/font packaging, non-Windows packaged-host empirical review, and the first bounded live runtime session loop.
- [ ] Pin the first `0.2.0` frame stack so the project transitions directly from `0.1.0` closeout into orchestration-ownership work instead of reopening the finished publication lane.

## Testing and validation plan

### Host matrix

| Host OS | Priority                 |
| ------- | ------------------------ |
| Windows | Highest                  |
| Linux   | High                     |
| macOS   | Later / optional for MVP |

### Device matrix

| Device tier                                     | Purpose                     |
| ----------------------------------------------- | --------------------------- |
| one older known-Heimdall-friendly Galaxy device | backend bring-up            |
| one mid-generation Samsung device               | workflow validation         |
| one newer Samsung device                        | restriction/risk validation |

### Test categories

| Category                        | Example checks                                                                                               |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| transport tests                 | device detection, session start, PIT download                                                                |
| manifest tests                  | checksum mismatch, wrong product code, missing PIT                                                           |
| flash-plan tests                | recovery-only plan, no-reboot path, repartition blocked by default                                           |
| package-intake security tests   | archive traversal, absolute paths, symlink abuse, duplicate partition targets, package mutation after review |
| suspiciousness heuristics tests | Magisk markers, `test-keys`, insecure props, AVB or dm-verity disablement, permissive SELinux                |
| execution-path integrity tests  | acknowledgement bypass attempts, non-ready execution requests, reviewed-plan drift                           |
| parser/normalizer abuse tests   | malformed manifests, oversized fields, hostile transport output, contradictory progress lines                |
| Windows driver tests            | missing driver, wrong driver, post-Zadig detection                                                           |
| resilience tests                | disconnect, USB hub issues, cable replacement guidance                                                       |
| UX tests                        | destructive warning clarity, report export completeness                                                      |

Current implementation note for the publication lane: the shared security validation suite already enforces dangerous-pattern scanning, explicit companion subprocess timeouts, and safe release-lane zip extraction. Checksum placeholders, the real package archive importer, and Android-image suspiciousness heuristics remain warning-tier carry-forward debt rather than blocking-pass surfaces.

### Safety gates before any live flash

- use non-primary lab devices only
- confirm device model and product code independently
- confirm battery is high enough
- use direct motherboard USB port when possible
- avoid hubs and questionable cables
- capture PIT and logs before destructive actions

## Risk register

| Risk                                                  | Severity | Mitigation                                                                                                |
| ----------------------------------------------------- | -------- | --------------------------------------------------------------------------------------------------------- |
| wrong firmware on wrong Samsung variant               | Critical | product-code enforcement + PIT validation + package compatibility rules                                   |
| repartition misuse                                    | Critical | off by default, advanced-only gating, repeated confirmations                                              |
| Windows driver confusion                              | High     | automated diagnostics and guided driver install                                                           |
| unsupported new Samsung restrictions                  | High     | device registry, feature flags, hardware validation lane                                                  |
| stale inherited Heimdall code                         | High     | backend isolation, modernization, tests, and sprint-by-sprint replacement rather than indefinite wrapping |
| sprint scope too small to move autonomy meaningfully  | High     | enforce minor-version sprint boundaries as substantial `0.X.0` milestones                                 |
| GUI under-scoped or treated as cosmetic               | High     | make GUI mandatory in the architecture and phase plan from day one                                        |
| unsafe package archive intake                         | High     | safe extractor boundary, path normalization, duplicate-target rejection, and payload size limits          |
| reviewed package changes before execution             | High     | sealed analyzed-package snapshot plus pre-execution rehash                                                |
| suspicious custom package traits hidden from operator | High     | Android image heuristics, bypassable warning model, and evidence capture                                  |
| style drift away from CodeSentinel brand              | Medium   | codify the visual system early and review against reference dashboards                                    |
| cable/USB instability                                 | Medium   | preflight guidance, retry/resume support, explicit troubleshooting                                        |
| legal/trademark confusion with Odin branding          | Medium   | avoid Odin name, avoid bundling leaked binaries, keep project identity independent                        |
| package provenance issues                             | Medium   | checksums, signatures, source metadata                                                                    |
| overtrusting backend-output normalization             | Medium   | adversarial parser tests and stricter event-normalization contracts                                       |

## Practical recommendation for the project

If this project needs a **credible, buildable plan**, the best answer is:

> Build a new Samsung-first flashing platform by starting from Heimdall, then replacing it in six substantial sprint releases until the supported matrix reaches full runtime autonomy at `0.6.0`, with the GUI, safety model, and orchestration layer leading the product from Sprint 1.

If this project needs a **prototype scope**, then the best MVP is:

- Windows + Linux support
- Samsung download-mode detection
- PIT download + print
- recovery-partition flashing for a vetted device subset
- package validation with product-code checks
- exportable flash reports

That is ambitious enough to be meaningful and constrained enough to be realistic.

## Final recommendation

### Recommended thesis statement

A successful open-source Samsung-oriented Android flashing platform should treat **Heimdall as the initial protocol base**, **the mandatory GUI as a primary product surface**, **PIT-aware validation as the safety core**, and **a six-sprint staged replacement path to runtime autonomy** as the main implementation strategy.

### Recommended deliverable framing

| Deliverable                | Recommendation                                                                                                                  |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| research conclusion        | Heimdall is the correct open-source starting point, but not the permanent dependency target                                     |
| architecture conclusion    | layered platform with Samsung backend, package validator, registry, mandatory GUI, and secondary CLI                            |
| project scope conclusion   | Samsung-first, GUI-first staged replacement path over six substantial sprint releases                                           |
| differentiation conclusion | safer validation, device-aware packaging, strong operations UX, diagnostics, reproducibility, and a deliberate autonomy roadmap |

## Sources

### Primary / technical sources

- Heimdall GitHub repository: https://github.com/Benjamin-Dobell/Heimdall
- Heimdall README (raw): https://raw.githubusercontent.com/Benjamin-Dobell/Heimdall/master/README.md
- Heimdall Windows README (raw): https://raw.githubusercontent.com/Benjamin-Dobell/Heimdall/master/Win32/README.txt
- Heimdall Linux README (raw): https://raw.githubusercontent.com/Benjamin-Dobell/Heimdall/master/Linux/README
- Glass Echidna Heimdall page: https://glassechidna.com.au/heimdall/
- AOSP fastboot flashing docs: https://source.android.com/docs/setup/test/running
- AOSP Android Flash Tool docs: https://source.android.com/docs/setup/test/flash
- AOSP fastboot key combinations: https://source.android.com/docs/setup/reference/fastboot-keys
- Android Developers `adb` docs: https://developer.android.com/studio/command-line/adb

### Supporting / secondary sources

- Wikipedia overview of Odin and Heimdall context: https://en.wikipedia.org/wiki/Odin_(firmware_flashing_software)
- LineageOS Heimdall recovery install example: https://wiki.lineageos.org/devices/i9300/install/#installing-a-custom-recovery-using-heimdall

### Unverified emerging-risk lead

- Android Authority article referenced by Wikipedia regarding 2026 Samsung download-mode changes could not be fetched from this environment. Treat the claim as a research lead requiring hardware validation before it informs hard product rules.
