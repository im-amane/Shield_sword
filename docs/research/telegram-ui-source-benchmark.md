# Telegram Bot UI & Source Architecture Benchmark

**Project:** Ani World Guardian (`im-amane/Shield_sword`)  
**Research status:** Evidence-backed interim report; source-code and visual review still requires a final pass before implementation.  
**Prepared:** 2026-11-19  
**Scope:** Open-source Telegram moderation bots, their interaction patterns, and compatibility with Guardian. This document is a research record, not permission to deploy unreviewed features.

## Executive summary

The most useful lessons are not another pile of moderation commands. Guardian already has CAPTCHA, anti-spam, anti-link, bad-word filtering, raid protection, warnings, moderation, audit/security history, encrypted backup flow, and a private owner panel. The best next gains are likely:

1. A more coherent, mobile-first owner-panel navigation and consistent status/action presentation.
2. Per-community settings and permission-aware controls, rather than global toggles that can affect the wrong group.
3. Safer confirmation and callback handling for destructive actions.
4. A verifiable backup recovery workflow and explicit retention policy.
5. A user appeal/review workflow only after its abuse model, authorization and data retention are designed.

No production code was changed during this research pass.

## 1. Reference projects

### 1.1 Rose / MissRose family

- Repository reference: https://github.com/khamdamoff/missrose
- Documentation: https://missrose.org/docs/
- Relevant documentation: anti-spam blocklists, antiflood, antiraid and advanced settings.
- The research material describes a feature-oriented command/module structure: welcomes, notes, filters, locks, warnings, antiflood, antiraid and related group-management functions.
- The source family has multiple forks and variants. Framework, database and license claims must be checked against the exact repository and commit before reusing any code. Do not assume every project named Rose has the same license or architecture.
- Reusable design lesson: keep feature handlers isolated, give each feature discoverable help, and make configuration explicit. Do not copy a fork's code until its exact LICENSE and provenance are verified.

### 1.2 Shieldy

- Repository: https://github.com/1inch/shieldy
- Source layout includes distinct `commands`, `controllers` and `helpers` areas (repository tree).
- Its core workflow is newcomer detection -> candidate state -> challenge delivery -> verification or timeout handling.
- Public source/research references describe multiple CAPTCHA styles and message templates with placeholders such as username, group title, challenge and time limit.
- License: the repository identifies itself as MIT; verify the current LICENSE file at the point of any code reuse.
- Reusable design lesson: separate verification state from message rendering, make challenge copy configurable, and keep expiry/retry transitions explicit.
- Guardian already has an arithmetic CAPTCHA and pending-verification persistence. The safe candidate is improved templates and configurable challenge settings, not a second CAPTCHA engine without a demonstrated need.

### 1.3 Shield (redstone-md)

- Repository: https://github.com/redstone-md/shield
- The repository describes a local fast-path moderation pipeline, optional slower model/vision checks, SQLite by default with PostgreSQL support, and an optional web server/API.
- Its published admin interface includes message checking, sample/dictionary management, approved-user management, detected-spam history and settings. Its appeal flow uses explicit accept/reject actions.
- License: repository identifies MIT; re-check the exact LICENSE before copying any code.
- Reusable design lesson: separate detection from enforcement, retain structured incident state, and make review decisions explicit and auditable.
- Guardian already has incident/audit storage and an owner dashboard. The web UI and LLM/vision pipeline are not recommended for the next phase: they add hosting, privacy, cost and operational complexity.

### 1.4 Combot

- Product site: https://combot.org/
- Commercial/proprietary product; use only as a functional and UX benchmark, not a source-code reference.
- Public feature descriptions include analytics, automations, member reports, moderation tools and under-attack/read-only modes.
- Reusable design lesson: show administrators concise operational summaries and clear action states.
- Avoid mass-removal and member-profiling features unless a narrow, justified and explicitly confirmed use case exists. They are not a default roadmap item.

### 1.5 Telegram native admin tools

- Official Bot API: https://core.telegram.org/bots/api
- Official Bot FAQ: https://core.telegram.org/bots/faq
- Prefer native Telegram permissions, admin status and update types over maintaining shadow copies of Telegram state.
- Handle API errors and rate limits, including `retry_after`, without retry storms.
- Privacy and developer terms: https://telegram.org/tos/bot-developers
- Do not scrape chat history, infer private identity, or collect IP/device/phone information.

## 2. UI and interaction benchmark

### Patterns worth adopting

- **One clear dashboard home:** identity/status, monitored-community count, recent incidents, active raid state, and a small number of high-value navigation choices.
- **Consistent navigation:** every section should have predictable Home, Refresh and Close actions. Callback data should be namespaced and validated.
- **Short mobile-first sections:** compact headings, one or two buttons per row, avoid dense walls of text, and paginate long histories.
- **Status before controls:** display current state, scope (which group), and last-updated time before presenting a toggle.
- **Confirm destructive actions:** show target, group, reason and consequence; require a second explicit confirmation for ban, mass action, restore, or irreversible changes.
- **Feedback:** after a successful action, show what changed and provide a safe undo/recovery path where possible.
- **Empty and error states:** explain why data is unavailable and how to fix it, rather than showing a blank panel.
- **Safe text rendering:** HTML-escape user-controlled names, titles and metadata; bound lengths; never render secrets.

### Proposed Guardian owner-panel specification

1. **Home:** bot health, monitored groups, 24-hour incident count, active protection state, latest backup/report delivery.
2. **Communities:** paginated list; selecting one opens a scoped overview. No global setting change without displaying the target community.
3. **Protection:** per-community CAPTCHA, anti-link, anti-spam, bad-word and raid state; read-only status first, then permission-checked controls.
4. **Activity:** privacy-minimized join events and security events, paginated, with retention notice.
5. **Security history:** severity, action, community, timestamp and minimal actor/target identifiers; no message-body archive.
6. **System health:** DB integrity, DB size, WAL mode, scheduler state, last successful backup/report, and sanitized diagnostics.
7. **Backup & recovery:** backup status and fingerprint only; no key display. Recovery must be offline/staged, integrity-checked and never overwrite the live DB without an explicit, separately protected operation.
8. **Configuration:** show presence/status of environment variables, never values of tokens, encryption keys or credentials.
9. **Automations:** show enabled/disabled, next/last run and last success/failure. Avoid claiming success based only on task creation.
10. **Command index:** categorized commands, permission level and group/private context.

Visual language: keep the existing Guardian identity (shield/royal theme) but standardize typography, spacing, icon meaning and status vocabulary. Do not add decorative emoji to every line at the expense of scanability.

## 3. Guardian compatibility inventory

Repository paths inspected on the `main` branch include:

- `app/main.py`, `app/config.py`, `app/storage.py`, `app/ui.py`, `app/backup_crypto.py`
- `app/security/owner.py`
- `app/handlers/panel.py`, `owner.py`, `moderation.py`, `warnings.py`, `verification.py`, `raid_protection.py`, `antispam.py`, `antilink.py`, `badwords.py`, `welcome.py`, `permission_monitor.py`, `diagnostics.py`, `security_status.py`, `start.py`
- `tests/test_panel.py`

The current owner panel already contains Protection, Communities, Member Watch, Security History, System Health, Secure Backup, Configuration, Automations and Command Index sections. It uses inline keyboards, a private owner-only access model, HTML escaping for displayed user-controlled values, and a premium typography helper. The test suite includes navigation, configuration-secret-redaction and automation/database display checks.

Existing feature coverage (based on repository structure and project implementation notes):

| Capability | Guardian status | Research implication |
|---|---|---|
| CAPTCHA / newcomer verification | Implemented | Improve templates/settings only after checking edge cases |
| Anti-spam / antiflood | Implemented | Tune and test; do not duplicate |
| Anti-link / domain allowlist | Implemented | Add scoped UI controls if missing |
| Bad-word filtering | Implemented | Add scoped UI controls if missing |
| Raid protection | Implemented | Surface status and safe configuration |
| Warnings / moderation | Implemented | Consider review/appeal only as a separate design |
| Audit / security incidents | Implemented | Improve pagination, filters and retention |
| Encrypted backups | Encryption path implemented | Recovery/restore verification remains a priority gap |
| Owner panel | Implemented | Improve scope clarity, consistency and pagination |
| Multi-community settings | Requires code-level verification | High-priority audit before adding UI toggles |

This inventory is not a claim that every feature has been live-tested in Telegram. CI tests and live Telegram permission checks are separate evidence.

## 4. Prioritized implementation backlog

| Priority | Candidate | Effort | Risk | Dependencies / acceptance criteria |
|---|---|---:|---:|---|
| P0 | Verify per-community setting model and callback authorization | Medium | High | Inspect storage schema and every panel callback; prove one group's settings cannot alter another |
| P0 | Backup decrypt/restore verification in isolated staging DB | Medium | Critical | Never touch live DB; validate AES-GCM authentication, SQLite integrity and expected schema |
| P1 | Panel pagination + consistent section navigation/status cards | Medium | Low | Unit tests for callbacks, pagination boundaries, HTML escaping and mobile-sized output |
| P1 | Per-community protection overview and safe toggles | Medium | High | Explicit group selection, fresh admin permission check, audit event, confirmation for risky changes |
| P1 | Data-retention policy for audit/incident/join metadata | Medium | Medium | Document defaults, test retention boundaries, preserve required security evidence |
| P2 | Moderation appeal/review workflow | High | Medium | Threat model for spam/abuse, one appeal per incident, reviewer authorization, idempotent decisions, audit trail |
| P2 | Configurable CAPTCHA templates and challenge modes | Medium | Medium | Placeholder allowlist, HTML-safe rendering, timeout/retry regression tests |
| P3 | Aggregate analytics | Low | Low | Counts only; no invasive member profiling or message-content collection |
| Defer | Web dashboard, LLM/vision moderation, mass moderation | High | High | Not justified until operational need, privacy review and hosting/security design exist |

## 5. Test and rollback plan

- Run existing unit suite and CI before and after each change.
- Test callback authorization for owner, non-owner, group admin, stale callback, forged callback and wrong-community context.
- Test all panel sections with empty, large and malformed metadata; ensure output remains under Telegram message limits.
- Test pagination first/last page, stale cursor and deleted community.
- Test setting isolation across two separate test groups.
- Test Telegram permission loss and recovery; no retry storm.
- Test backup decrypt in a temporary directory and SQLite integrity check; test wrong key and tampered ciphertext rejection.
- For schema changes, take a backup first, version migrations, and test migration/rollback against a copy of production data.
- Deploy only after CI passes; check Railway logs and health after deploy. Live Telegram group/channel checks remain a separate manual gate.
- Roll back with a Git revert and previous known-good deployment; do not run destructive DB rollback scripts against production.

## 6. License and compliance notes

- Repository names are not enough to establish licensing. Before copying code, inspect the exact upstream `LICENSE`, source file headers and commit. Preserve notices and attribution for any reused code.
- Prefer reimplementing general design patterns rather than copying large code blocks.
- Combot is proprietary; no source-code reuse.
- Minimize stored personal data. Do not collect IP addresses, device identifiers, phone numbers, private-message contents or inferred identities.
- Do not expose bot tokens, encryption keys or credentials in Telegram UI, logs, screenshots or this documentation.
- Do not scrape group history or build datasets from members' content.
- Mass actions must not be automatic defaults; any future bulk action needs a preview, explicit confirmation, permission recheck and audit event.

## 7. Sources

Primary project references:

- Rose/MissRose: https://github.com/khamdamoff/missrose
- Rose docs: https://missrose.org/docs/
- Shieldy: https://github.com/1inch/shieldy
- Shield: https://github.com/redstone-md/shield
- Combot product documentation: https://combot.org/
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bot FAQ: https://core.telegram.org/bots/faq
- Telegram Bot Developer Terms: https://telegram.org/tos/bot-developers
- Guardian repository: https://github.com/im-amane/Shield_sword

## 8. Remaining research before implementation

This report is an interim decision document, not a claim that every upstream source file and visual demo has been exhaustively inspected. Before implementation, complete and record:

1. Exact upstream commit hashes, current maintenance signals and LICENSE contents for every source project.
2. Source-level review of Shieldy's candidate lifecycle, timeout/retry and template rendering; Shield's detection/enforcement separation, storage migrations and web-admin auth; and the exact Rose fork selected for any pattern.
3. Real UI screenshot/demo review with dated references. Do not invent screenshots or infer visual details from README feature lists.
4. A callback-by-callback audit of Guardian's panel and a schema-level audit of per-chat settings.
5. A final implementation plan tied to exact Guardian files and regression tests.

**Decision:** research findings may guide a later implementation branch, but do not merge third-party code or alter production behavior until the remaining checks above are complete.
