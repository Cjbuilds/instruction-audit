# What we tested

On September 8, 2026, we sent the released prompt and four complete, line-numbered example file sets to `claude-fable-5-1` through the Claude subscription. Each final case ran once in an isolated text-only session, with tools disabled. A test-only JSON format was appended so citations and proposed edits could be checked. The normal prompt returns a readable audit.

| Case | Observed result |
|---|---|
| Real conflict | Found the test/skip-tests conflict, cited both exact lines, preserved security checks and proposed one changed line. It explicitly noted that maintainer precedence was unknown. |
| Broken link | Found the missing release checklist and proposed a one-line link repair to the replacement named in the supplied files. |
| Scoped context | Left the different Python/TypeScript scopes alone and found the separate broken checklist link. Proposed one changed line. |
| Clean control | Returned clean with no actions or patches. |

All four saved outputs pass `python3 scripts/check.py`. That checks exact citations, expected findings and link states, required preservation citations, and edit bounds. The proposed changes were also read manually: they keep the test/security gates intact. Nothing was applied to the fixture files.

## Review repairs

An independent reviewer found that the first checker could accept edits to protected rules. The checker now rejects edits to required preserved lines and edits not tied to cited actions. It also rejects malformed action entries without crashing and verifies the published input/output hashes. The prompt now requires an explicit instruction-file list in file-reading mode. Four fresh trials were run after that clarification; the [first-pass inputs and outputs](first-pass/) remain available. No model response was manually repaired.

## What this does not prove

No planted issue was missed in these four trials. That is a small behavioral check, not a general accuracy rate. We did not run a baseline without the prompt, so this is not evidence of improvement or token savings. We did not test another model, a live filesystem-reading agent, inaccessible files, external links, or all possible instruction conflicts. The normal Markdown presentation was not scored by this JSON-mode check.

The checker cannot decide whether a recommendation is wise. Exact preservation citations do not by themselves prove a patch preserves their meaning; inspect the proposed diff. Unknown intent still needs a human decision.

## Inspect or repeat

- [Saved responses](../results/): actual model output, unchanged.
- [Input packets](../inputs/): exact prompt plus supplied case; no answer key sent to the model.
- [Provider and hash receipts](receipts.json): requested/observed model, usage and file hashes. Account details omitted.
- [Fixtures and answer keys](../fixtures/): the source files and expected observations.

To repeat, send each input packet to your model in a fresh session, save its JSON response under the same case name in a separate results directory, and run `python3 scripts/check.py --evidence path/to/real-conflict.json` (repeat per case). A new run is new evidence; do not replace this published trial without recording it.
