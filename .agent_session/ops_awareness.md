# Ops Awareness Snapshot
**Snapshot:** 2026-04-23T00:07:25.967989Z  
**Session:** 20260422200725-calamum_vulcan  
**Hash:** `1448f3a3d920...`

## Up next (QuestStack)
- up next: (none)

## Job execution pipeline (canonical)
- Preferred: use the job orchestrators (start/close).
- Start: `codesentinel job start <task_id>`
- Close: `codesentinel job close <task_id>`

### Gate runner (IDE-agnostic; names-only)
- Preflight: `codesentinel gate preflight --timeout-sec 900 --lock-key gate_preflight`
- Pre-job: `codesentinel gate pre-job <task_id> --timeout-sec 900 --lock-key pre_job_<task_id>`
- Post-job: `codesentinel gate post-job --task-id <task_id> --rebuild-graph --timeout-sec 900 --lock-key post_job_rebuild_graph`

### Daily gates (standalone)
- BOD: `codesentinel gate bod --timeout-sec 900 --lock-key gate_bod`
- EOD (explicit): `codesentinel gate eod --explicit --timeout-sec 900 --lock-key gate_eod_explicit`

### Evidence surfaces
- Gate events: `logs/behavioral/gates/gate_events.jsonl`
- Reports: `logs/health_reports/operations`

## Search discipline (canonical)
- Quick reference: `docs/quick_reference/ORACALL_SEARCH_DISCIPLINE.md`
- Order: ORACall -> meaning-based -> file-glob -> exact string -> regex (last resort only)
- ORACall entrypoints:
  - search: `codesentinel oracall search`
  - trace: `codesentinel oracall trace`
  - stats: `codesentinel oracall stats`

## QuestStack scaffold-first (multi-frame jobs)
- Rule: For multi-frame jobs, create QuestStack doc/log/evidence before substantive work.
- Script: `operations/checklists/scripts/create_queststack_scaffold.py`

## Canonical checklist location
- `operations/checklists`

## Hard gates (canonical)
- Scripts directory: `tools/codesentinel/gates`
- Evidence stream: `logs/behavioral/gates/gate_events.jsonl`
- Evidence quick reference: `docs/quick_reference/GATE_EVIDENCE_LOCATIONS.md`

### Gate entrypoints
- BOD: `tools/codesentinel/gates/gate_bod.py`
- Preflight: `tools/codesentinel/gates/gate_preflight.py`
- Post-job: `tools/codesentinel/gates/gate_post_job.py`
- EOD: `tools/codesentinel/gates/gate_eod.py`

### BOD semantics (sticky)
- BOD is once per UTC day and satisfies all jobs for that day.
- Dedupe: UTC day (YYYY-MM-DD). Subsequent invocations are deduplicated.
- Evidence: `logs/behavioral/gates/gate_events.jsonl`
- Emergency repeat (not recommended): set `CODESENTINEL_ALLOW_REPEAT_BOD`=1

### Hard-gate rules

- BOD is once per UTC day; it satisfies all jobs for that day. Do not rerun BOD per job; reference the day's BOD evidence record instead. Emergency repeat only with CODESENTINEL_ALLOW_REPEAT_BOD=1.
- Use the hard-gate scripts (or VS Code tasks) for the correct scope: daily standalone gates (BOD, EOD) and per-run/per-job gates (Preflight, Post-job). EOD MUST NOT be treated as part of any per-job pipeline.
- Gates are fail-closed, non-interactive, timeout-bounded, and write exactly one JSONL evidence record per invocation.
- Do not rely on editor search to find gate evidence under logs/; use canonical paths instead.

## Core rules (recall)
- No plaintext sensitive identifiers (hosts, IPs, usernames, tokens, keys, passwords).
- Credentials are environment variables only (names-only in docs/logs).
- Archive-first: never delete; use quarantine_legacy_archive/.
- Prefer scripts over fragile one-liners (avoid CLI injection pitfalls).
- QuestStacks + evidence: track operational work with running doc + log + evidence.
- Run tests early/often; run full suite for policy-critical changes.
- Templates are governed artifacts: use VAULT templates or template pointers; do not invent ad-hoc report formats.

## Env var names (SSOT + adjunct; reference)
- SSOT: `tools/config/env/expected_env_vars.json`
- SSOT CLI: `codesentinel vault env ssot --profile <profile> --json`
- Validate CLI: `codesentinel vault env validate --profile <profile> --json`

## VAULT template library (mandatory)
- Root: `codesentinel/assets/VAULT_templates`
- Registry: `codesentinel/assets/VAULT_templates/INDEX.json`
- README: `codesentinel/assets/VAULT_templates/README.md`
- Agent instructions: `codesentinel/assets/VAULT_templates/AGENT_INSTRUCTIONS.md`

### Canonical report templates (examples)
- Job: `codesentinel/assets/VAULT_templates/reports/JOB_TEMPLATE.json.template` (paired: `codesentinel/assets/VAULT_templates/reports/JOB_TEMPLATE.md.template`)
- Job report: `codesentinel/assets/VAULT_templates/reports/JOB_REPORT_TEMPLATE.json.template` (paired: `codesentinel/assets/VAULT_templates/reports/JOB_REPORT_TEMPLATE.md.template`)
- Plan: `codesentinel/assets/VAULT_templates/reports/PLAN_TEMPLATE.json.template` (paired: `codesentinel/assets/VAULT_templates/reports/PLAN_TEMPLATE.md.template`)

### Template pointer conventions
- Markdown: `<!-- CODESENTINEL_TEMPLATE_POINTER: relative/or/absolute/path -->`
- JSON: `{'__codesentinel_template_pointer__': 'relative/or/absolute/path'}`
- Helper: `codesentinel/utils/template_pointers.py`

### Validation
- Validator: `tools/codesentinel/validate_reporting_templates.py`

---
_Auto-generated by SessionMemory_

