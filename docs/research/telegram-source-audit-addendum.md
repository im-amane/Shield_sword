# Telegram Bot Source Audit Addendum

**Prepared:** 2026-11-19  
**Repository:** `im-amane/Shield_sword`  
**Status:** Source-level review in progress; this addendum records verified findings, not a blanket endorsement of upstream behavior.

## 1. Exact upstream repositories and licenses

| Project | Default branch | Verified repository license | Maintenance signal checked |
|---|---|---|---|
| Shieldy (`1inch/shieldy`) | `master` | MIT | Repository metadata showed a 2026-02-09 push |
| Shield (`redstone-md/shield`) | `master` | MIT | Repository metadata showed a 2026-11-17 push |
| Rose Bot (`MRK-YT/Rose-Bot`) | `main` | GPL-3.0 | Repository metadata showed a 2024-02-03 push |
| MissRose (`khamdamoff/missrose`) | `master` | GPL-3.0 | Repository metadata showed a 2020-04-13 push |
| Combot | Proprietary service | No source license; no source reuse | Product/UX benchmark only |

License files were read directly from the exact repositories. Do not treat similarly named forks as interchangeable. In particular, the Shieldy README's historical clone URL points to a different repository name than the audited repository. Any future code reuse must be rechecked against the exact source commit and retain required notices. The Rose variants are GPL-3.0; prefer implementing general ideas independently unless the project deliberately accepts the applicable copyleft obligations.

## 2. Shieldy source findings

Reviewed:
- `src/helpers/newcomers/handleNewChatMembers.ts`
- `src/helpers/newcomers/getCandidate.ts`
- `src/helpers/newcomers/checkPassingCaptchaWithText.ts`
- `src/helpers/newcomers/checkButton.ts`
- `src/helpers/newcomers/kickCandidates.ts`
- `src/commands/captcha.ts`
- `src/commands/captchaMessage.ts`
- `src/middlewares/checkSuperAdmin.ts`

Verified design patterns:
1. A newcomer is represented by a candidate record containing the chat/user IDs, selected CAPTCHA type, challenge data, expiry timestamp and message references. This separates verification state from message presentation.
2. Admin-added members can bypass the newcomer gate; already-verified users can be skipped when configured.
3. The button handler checks that the callback's user ID matches the candidate and confirms the candidate is still pending before completing verification.
4. CAPTCHA mode and custom message are group-configurable, with the selected value persisted.
5. Candidate timeout/kick processing and entry-message cleanup are separate helpers.

Cautions:
- The button-tap de-duplication map is process-local. It is not a distributed lock and is not suitable as-is for multi-replica deployments.
- Some paths perform best-effort asynchronous deletion/greeting and report errors separately. Guardian should preserve explicit state transitions and awaited critical operations.
- The old-user ID heuristic, CAS dependency, global restriction behavior and automatic kick-on-attack policy are not adopted by default.

Guardian decision: retain the existing persistent CAPTCHA engine. Consider configurable, HTML-safe welcome/challenge templates and explicit challenge modes only after tests demonstrate a real gap.

## 3. Shield source findings

Reviewed:
- `app/events/admin_callbacks.go`
- `app/events/listener_helpers.go` callback authorization helper
- `app/events/callback_auth_test.go`
- `app/events/appeal_handler.go`
- `app/events/appeal_resolution.go`
- `app/audit/appeal.go`
- Repository README, license and UI asset inventory

Verified design patterns:
1. Inline admin callbacks are gated by both the configured admin chat and a superuser identity check. Tests cover unauthorized users, wrong chat and missing sender.
2. Ban and selected moderation decisions use a confirmation step before enforcement.
3. Appeal submission validates the incident ID, confirms the appellant is the affected user, rejects closed incidents and prevents duplicate submissions.
4. The project separates Telegram event handling, moderation policy, audit/appeal state and web control-plane services.
5. README documents SQLite/PostgreSQL persistence, versioned rule sets, an HTMX web UI and browser-based UI end-to-end tests.

Important caution: the reviewed appeal service updates appeal/incident state and then invokes several enforcement/notification side effects best-effort. Guardian must not copy this ordering blindly. Any appeal feature here needs an explicit transactional/outbox or recoverable state design so an accepted appeal cannot silently leave a member banned.

### Public UI asset references

The repository tree contains these documented UI images:
- [Message checker](https://github.com/redstone-md/shield/blob/master/site/docs/msg-checker.png)
- [Manage samples](https://github.com/redstone-md/shield/blob/master/site/docs/manage-samples.png)
- [Manage users](https://github.com/redstone-md/shield/blob/master/site/docs/manage-users.png)
- [Unban confirmation](https://github.com/redstone-md/shield/blob/master/site/docs/unban-confirmation.png)
- [Change ban](https://github.com/redstone-md/shield/blob/master/site/docs/change-ban.png)
- [Ban report](https://github.com/redstone-md/shield/blob/master/site/docs/ban-report.png)

These are reference assets from a web-admin product, not Telegram inline-panel screenshots. The useful interaction ideas are clear review states, explicit confirmation and separation of operational views. A web dashboard is not recommended for Guardian's next iteration because it would add a new exposed service and authentication surface.

## 4. Guardian code audit findings

Reviewed current `main` source:
- `app/handlers/panel.py`
- `app/storage.py`
- `app/security/owner.py`
- `app/ui.py`
- `app/backup_crypto.py`
- `app/main.py`
- `tests/test_panel.py`
- `app/handlers/raid_protection.py`

Confirmed:
- Owner identity comparison fails closed when IDs are absent or invalid.
- Anti-link and bad-word settings are keyed by `chat_id`; allowed domains and bad words are also group-scoped.
- Raid state and pending verification state are keyed by `chat_id`.
- The panel currently lists monitored communities but does not yet provide a selected-community protection detail view or per-community toggles.
- Security history, audit and member activity are currently global recent lists with fixed limits; pagination and per-community filters are missing.
- The panel already redacts secret values and displays only backup-key status/fingerprint.
- Backup encryption uses AES-256-GCM; decrypt/restore verification in an isolated staging database remains a separate P0 task.

### Callback scope issue found and fixed on a review branch

The owner-panel callback handler checked the owner identity first, but processed the `close` action before verifying that the callback message was in a private chat. This did not grant access to a non-owner, but it violated the panel's private-chat-only boundary.

PR #1 moved the private-chat scope check ahead of every action and added focused unit coverage:
- PR: https://github.com/im-amane/Shield_sword/pull/1
- Merged into `main` after CI passed.
- Railway deployment succeeded with 1/1 replica online; live Telegram button smoke testing remains a manual gate.

## 5. Implementation decisions

### Adopt
- Explicit per-community selection before showing or changing group protections.
- Fresh owner/admin authorization at the moment of every setting change.
- Callback namespace and payload validation, with stale/forged/wrong-chat tests.
- Two-step confirmation for destructive actions.
- Pagination and filters for activity/audit lists.
- Configurable, escaped CAPTCHA/welcome templates.
- Recoverable backup verification and staged restore.

### Do not adopt by default
- Process-local callback locks as a concurrency guarantee.
- Automatic mass kicks/bans based on weak heuristics.
- Invasive member profiling or private identity inference.
- LLM/vision moderation or a public web dashboard before a clear need and privacy/security review.
- Third-party appeal logic without reliable state/side-effect recovery.

## 6. Next audit and integration sequence

1. PR #1 callback hardening is merged and CI is green.
2. A read-only per-community detail view is being implemented on `feature/community-panel-readonly` using chat-scoped storage queries.
3. Tests cover two-community data isolation, pagination, escaped titles and read-only navigation.
4. After this view is verified, design the callback action layer with fresh permission checks, audit events and confirmation.
5. Complete encrypted-backup decrypt/integrity verification in an isolated temporary database.
6. Only then enable per-community controls in a separate implementation PR.
7. Deploy after CI and code review; live Telegram permission testing remains a manual gate.

## 7. Primary source links

- Shieldy source: https://github.com/1inch/shieldy
- Shieldy CAPTCHA candidate lifecycle: https://github.com/1inch/shieldy/tree/master/src/helpers/newcomers
- Shield source: https://github.com/redstone-md/shield
- Shield callback authorization tests: https://github.com/redstone-md/shield/blob/master/app/events/callback_auth_test.go
- Shield appeal handling: https://github.com/redstone-md/shield/tree/master/app/events
- Rose Bot source: https://github.com/MRK-YT/Rose-Bot
- MissRose source: https://github.com/khamdamoff/missrose
- Telegram Bot API: https://core.telegram.org/bots/api
- Telegram Bot FAQ: https://core.telegram.org/bots/faq
- Telegram Bot Developer Terms: https://telegram.org/tos/bot-developers
