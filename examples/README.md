# Good and bad audit responses

These are teaching examples, not measured model outputs. The actual trials are in [tests/results](../tests/results/).

## Good: explain the conflict, propose one change

> **Findings.** Two rules overlap for application changes.
>
> `AGENTS.md:4`: “Run tests for every application change.”
>
> `docs/workflow.md:3`: “Skip tests for application changes.”
>
> The same change cannot both run and skip tests. Neither file states precedence. I recommend keeping the test gate and changing the skip rule, subject to your review.
>
> Preserve `AGENTS.md:5`: “Never print credentials.”
>
> Proposed change to `docs/workflow.md:3`: replace “Skip tests for application changes.” with “Run tests for every application change.” No files changed.

The useful parts are exact evidence, overlapping scope, a small proposal, and an explicit unresolved decision. A confident guess about precedence is not evidence.

## Good: leave a clean file alone

> **Clean.** All supplied references resolve. Python applies to `scripts/`; TypeScript applies to `frontend/`. These rules govern different files. No changes proposed.

## Good: say what you cannot check

> **Incomplete.** `AGENTS.md:6` links to `docs/release.md`, but that file was not supplied and the inventory is not marked complete. It is unavailable to this audit; I cannot call it missing. Please supply it before deciding on a repair.

## Bad: rewrite without evidence

> Your AGENTS.md is confusing. Replace it with these ten best practices.

This invents a new system instead of identifying a real defect. There are no citations, no scoped explanation, and no reason to believe essential checks survived.

## Bad: invent a repair

> The checklist was not supplied. Delete its release requirement.

An unavailable file is not a missing file. Even a proven broken link is not permission to remove the underlying check.
