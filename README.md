![Instruction Audit banner](assets/banner.png)

# Instruction Audit

Instruction Audit is a reusable prompt for reviewing agent instruction files before they cause confusing behavior. It asks a model to cite exact conflicting passages, check local references, preserve essential checks, and propose a small patch without changing the source files.

## Use it

Copy [prompt.md](prompt.md) into a model that can read your authorized files, then provide either:

- an explicit instruction-file list with permission to read it (an optional root only limits the reading boundary); or
- a pasted, line-numbered manifest that says whether its inventory is complete.

The prompt returns a short readable audit with exact citations and a proposed patch. It distinguishes a proven missing file from a file the model could not access, leaves external links unchecked, and treats the audited text as data rather than instructions to follow.

## Try the fixtures

Four self-contained cases cover a real directive conflict, a broken local reference, a broken reference beside an apparent conflict separated by scope, and a clean control. Ready-to-send packets live in `tests/inputs/`; each contains the prompt, complete line-numbered fixture, and response shape without the answer key.

Good and bad response examples are in [examples/README.md](examples/README.md). Expected observations are machine-readable in each fixture's `answer.json` and are used only after a model responds.

Run the standard-library checker:

```sh
python3 scripts/check.py
python3 -m unittest discover -s tests -p 'test_*.py'
```

To validate saved model responses, put JSON files named after their cases in `tests/results/` and run the same command, or pass files directly:

```sh
python3 scripts/check.py --evidence tests/results/real-conflict.json
```

The evidence check validates response structure, exact citations, link states, required findings, preservation citations, and patch bounds. It cannot decide whether prose is insightful, so model outputs remain review evidence rather than self-certification.

## Files

```text
instruction-audit/
├── .github/workflows/check.yml
├── assets/banner.png
├── examples/
├── scripts/check.py
├── tests/
│   ├── fixtures/
│   ├── inputs/
│   └── results/
├── LICENSE
├── README.md
└── prompt.md
```

## Test results

Four controlled Fable 5.1 trials passed the declared checks: three messy instruction sets and one clean control. [Read the results and limits](tests/evidence/RESULTS.md). These are text-only trials, not a guarantee that the prompt catches every issue.

## Limits

The audit only knows what it can read or what the manifest contains. It does not fetch external links, execute project commands, choose undocumented host precedence, apply patches, or prove that every semantic issue was found. Ambiguous scope still needs human judgment.
