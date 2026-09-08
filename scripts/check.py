#!/usr/bin/env python3
"""Build evaluation packets and validate the Instruction Audit package/evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
INPUTS = ROOT / "tests" / "inputs"
RESULTS = ROOT / "tests" / "results"
CASE_IDS = ("real-conflict", "broken-link", "scoped-context", "clean-control")
TOP_LEVEL_KEYS = {
    "schema_version",
    "mode",
    "status",
    "summary",
    "coverage",
    "conflicts",
    "links",
    "preserve",
    "actions",
    "patches",
    "uncertainties",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read valid JSON from {path.relative_to(ROOT)}: {exc}") from exc


def read_case(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    fixture = load_json(FIXTURES / case_id / "fixture.json")
    answer = load_json(FIXTURES / case_id / "answer.json")
    if not isinstance(fixture, dict) or not isinstance(answer, dict):
        raise ValueError(f"{case_id}: fixture and answer must be JSON objects")
    return fixture, answer


def line_map(fixture: dict[str, Any]) -> dict[tuple[str, int], str]:
    result: dict[tuple[str, int], str] = {}
    for entry in fixture["files"]:
        for number, line in enumerate(entry["lines"], start=1):
            result[(entry["path"], number)] = line
    return result


def packet_text(prompt: str, response_format: str, fixture: dict[str, Any]) -> str:
    inventory = "\n".join(f"- `{path}`" for path in fixture["inventory"])
    rendered_files: list[str] = []
    for entry in fixture["files"]:
        numbered = "\n".join(
            f"{number:>3} | {line}" for number, line in enumerate(entry["lines"], start=1)
        )
        rendered_files.append(f"### `{entry['path']}`\n\n```text\n{numbered}\n```")
    contents = "\n\n".join(rendered_files)
    return (
        "# Instruction Audit evaluation input\n\n"
        f"Case ID: `{fixture['case_id']}`\n\n"
        "Send this packet as one user message. Return only the JSON object required by the prompt.\n\n"
        "## Auditor prompt\n\n"
        f"{prompt.rstrip()}\n\n"
        "## Supplied fixture\n\n"
        "Use `pasted_manifest` mode. The inventory below is explicitly complete. "
        "The line-number prefixes are presentation metadata and are not part of the quoted lines.\n\n"
        "### Complete inventory\n\n"
        f"{inventory}\n\n"
        "### Line-numbered file contents\n\n"
        f"{contents}\n\n"
        f"{response_format.rstrip()}\n"
    )


def validate_fixture(case_id: str, failures: list[str]) -> None:
    try:
        fixture, answer = read_case(case_id)
    except ValueError as exc:
        failures.append(str(exc))
        return

    if fixture.get("schema_version") != 1 or answer.get("schema_version") != 1:
        failures.append(f"{case_id}: schema_version must be 1")
    if fixture.get("case_id") != case_id or answer.get("case_id") != case_id:
        failures.append(f"{case_id}: case_id does not match directory")
    if fixture.get("mode") != "pasted_manifest" or fixture.get("inventory_complete") is not True:
        failures.append(f"{case_id}: fixture must declare a complete pasted manifest")

    inventory = fixture.get("inventory")
    files = fixture.get("files")
    if not isinstance(inventory, list) or not all(isinstance(item, str) for item in inventory):
        failures.append(f"{case_id}: inventory must be a string list")
        return
    if not isinstance(files, list):
        failures.append(f"{case_id}: files must be a list")
        return

    listed: list[str] = []
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {"path", "lines"}:
            failures.append(f"{case_id}: each file entry needs only path and lines")
            continue
        path = entry.get("path")
        lines = entry.get("lines")
        if not isinstance(path, str) or not isinstance(lines, list) or not all(
            isinstance(line, str) for line in lines
        ):
            failures.append(f"{case_id}: invalid file entry")
            continue
        if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            failures.append(f"{case_id}: unsafe fixture path {path!r}")
            continue
        listed.append(path)
        actual = FIXTURES / case_id / "files" / path
        if not actual.is_file():
            failures.append(f"{case_id}: missing physical fixture file {path}")
            continue
        if actual.read_text(encoding="utf-8").splitlines() != lines:
            failures.append(f"{case_id}: line inventory differs from files/{path}")

    physical = sorted(
        path.relative_to(FIXTURES / case_id / "files").as_posix()
        for path in (FIXTURES / case_id / "files").rglob("*")
        if path.is_file()
    )
    if sorted(inventory) != sorted(listed) or sorted(inventory) != physical:
        failures.append(f"{case_id}: complete inventory does not exactly match file entries and files/")

    required_answer_keys = {
        "schema_version",
        "case_id",
        "expected_status",
        "required_conflicts",
        "required_links",
        "required_preserve",
        "required_action_kinds",
        "allowed_patch_paths",
        "max_patch_changed_lines",
        "require_no_patches",
        "require_no_conflicts",
    }
    if set(answer) != required_answer_keys:
        failures.append(f"{case_id}: answer.json keys do not match the answer schema")


def check_local_links(path: Path, text: str, failures: list[str]) -> None:
    for target in re.findall(r"!?\[[^]]*\]\(([^)]+)\)", text):
        if re.match(r"(?:https?://|mailto:|#)", target):
            continue
        clean_target = target.split("#", 1)[0]
        if not (path.parent / clean_target).exists():
            failures.append(f"{path.relative_to(ROOT)}: broken local link {target}")


def validate_package(write_inputs: bool) -> list[str]:
    failures: list[str] = []
    required = (
        ROOT / "README.md",
        ROOT / "prompt.md",
        ROOT / "LICENSE",
        ROOT / "assets" / "banner.png",
        ROOT / "examples" / "README.md",
        ROOT / "tests" / "response-format.md",
        ROOT / ".github" / "workflows" / "check.yml",
    )
    for path in required:
        if not path.is_file():
            failures.append(f"missing required file: {path.relative_to(ROOT)}")

    if (ROOT / "README.md").is_file():
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        check_local_links(ROOT / "README.md", readme, failures)
        for expected in ("assets/banner.png", "prompt.md", "python3 scripts/check.py"):
            if expected not in readme:
                failures.append(f"README.md is missing {expected!r}")
    if (ROOT / "LICENSE").is_file() and "Copyright (c) 2026 CJ Zafir" not in (
        ROOT / "LICENSE"
    ).read_text(encoding="utf-8"):
        failures.append("LICENSE must use CJ Zafir copyright")

    prompt_path = ROOT / "prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.is_file() else ""
    response_format_path = ROOT / "tests" / "response-format.md"
    response_format = response_format_path.read_text(encoding="utf-8") if response_format_path.is_file() else ""
    for case_id in CASE_IDS:
        validate_fixture(case_id, failures)
        if not prompt or not response_format:
            continue
        try:
            fixture, _ = read_case(case_id)
        except ValueError:
            continue
        expected_packet = packet_text(prompt, response_format, fixture)
        packet_path = INPUTS / f"{case_id}.md"
        if write_inputs:
            packet_path.write_text(expected_packet, encoding="utf-8")
        elif not packet_path.is_file():
            failures.append(f"missing generated input packet: tests/inputs/{case_id}.md")
        elif packet_path.read_text(encoding="utf-8") != expected_packet:
            failures.append(f"tests/inputs/{case_id}.md is stale; run scripts/check.py --write-inputs")
        if packet_path.is_file() and "required_conflicts" in packet_path.read_text(encoding="utf-8"):
            failures.append(f"tests/inputs/{case_id}.md leaks answer-key fields")

    expected_case_set = set(CASE_IDS)
    actual_case_set = {path.name for path in FIXTURES.iterdir() if path.is_dir()}
    if actual_case_set != expected_case_set:
        failures.append("fixture directories must be exactly the four declared cases")
    return failures


def citation_key(value: Any, lines: dict[tuple[str, int], str], label: str, failures: list[str]) -> tuple[str, int] | None:
    if not isinstance(value, dict) or set(value) != {"path", "line", "quote"}:
        failures.append(f"{label}: citation must contain only path, line, and quote")
        return None
    path, number, quote = value.get("path"), value.get("line"), value.get("quote")
    if not isinstance(path, str) or not isinstance(number, int) or not isinstance(quote, str):
        failures.append(f"{label}: citation fields have invalid types")
        return None
    expected = lines.get((path, number))
    if expected is None:
        failures.append(f"{label}: citation points outside supplied content: {path}:{number}")
        return None
    if quote != expected:
        failures.append(f"{label}: quote is not the exact complete line at {path}:{number}")
        return None
    return path, number


def validate_evidence(path: Path) -> list[str]:
    failures: list[str] = []
    case_id = path.stem
    if case_id not in CASE_IDS:
        return [f"{path}: filename stem must be one of {', '.join(CASE_IDS)}"]
    try:
        response = load_json(path)
        fixture, answer = read_case(case_id)
    except ValueError as exc:
        return [str(exc)]
    if not isinstance(response, dict):
        return [f"{path}: response must be one JSON object"]
    if set(response) != TOP_LEVEL_KEYS:
        failures.append(f"{path.name}: top-level keys do not match the required response shape")
        return failures
    if response.get("schema_version") != 1:
        failures.append(f"{path.name}: schema_version must be 1")
    if response.get("mode") != "pasted_manifest":
        failures.append(f"{path.name}: mode must be pasted_manifest")
    if response.get("status") != answer["expected_status"]:
        failures.append(f"{path.name}: expected status {answer['expected_status']!r}")
    if not isinstance(response.get("summary"), str) or not response["summary"].strip():
        failures.append(f"{path.name}: summary must be nonempty")
    for key in ("coverage", "conflicts", "links", "preserve", "actions", "patches", "uncertainties"):
        if not isinstance(response.get(key), list):
            failures.append(f"{path.name}: {key} must be a list")
    if failures:
        return failures

    lines = line_map(fixture)
    coverage = response["coverage"]
    coverage_states: dict[str, str] = {}
    for index, item in enumerate(coverage):
        if not isinstance(item, dict) or set(item) != {"path", "state", "reason"}:
            failures.append(f"{path.name}: coverage[{index}] has invalid shape")
            continue
        if item["state"] not in {"read", "missing", "unavailable"} or not isinstance(item["reason"], str):
            failures.append(f"{path.name}: coverage[{index}] has invalid values")
            continue
        coverage_states[item["path"]] = item["state"]
    for supplied in fixture["inventory"]:
        if coverage_states.get(supplied) != "read":
            failures.append(f"{path.name}: supplied file {supplied} must have read coverage")

    conflict_citation_sets: list[tuple[str, set[tuple[str, int]]]] = []
    for index, conflict in enumerate(response["conflicts"]):
        if not isinstance(conflict, dict) or set(conflict) != {
            "id", "classification", "scope", "passages", "explanation"
        }:
            failures.append(f"{path.name}: conflicts[{index}] has invalid shape")
            continue
        if conflict["classification"] not in {"conflict", "ambiguity"} or not isinstance(conflict["passages"], list):
            failures.append(f"{path.name}: conflicts[{index}] has invalid values")
            continue
        keys = {
            key for key in (
                citation_key(item, lines, f"{path.name} conflicts[{index}]", failures)
                for item in conflict["passages"]
            ) if key is not None
        }
        conflict_citation_sets.append((conflict["classification"], keys))
    if answer["require_no_conflicts"] and response["conflicts"]:
        failures.append(f"{path.name}: case has no true conflicts")
    for required in answer["required_conflicts"]:
        required_keys = {(item["path"], item["line"]) for item in required["citations"]}
        if not any(kind == required["classification"] and required_keys <= keys for kind, keys in conflict_citation_sets):
            failures.append(f"{path.name}: missing required conflict evidence {sorted(required_keys)}")

    observed_links: set[tuple[str, int, str, str]] = set()
    for index, link in enumerate(response["links"]):
        if not isinstance(link, dict) or set(link) != {"source", "target", "state", "reason"}:
            failures.append(f"{path.name}: links[{index}] has invalid shape")
            continue
        source = citation_key(link["source"], lines, f"{path.name} links[{index}]", failures)
        if source and link["state"] in {"exists", "missing", "unavailable", "external_unchecked"}:
            observed_links.add((source[0], source[1], link["target"], link["state"]))
        else:
            failures.append(f"{path.name}: links[{index}] has invalid state")
    for required in answer["required_links"]:
        key = (required["source_path"], required["source_line"], required["target"], required["state"])
        if key not in observed_links:
            failures.append(f"{path.name}: missing required link observation {key}")
        if required["state"] == "missing" and coverage_states.get(required["target"]) != "missing":
            failures.append(f"{path.name}: missing link target {required['target']} needs missing coverage")

    preserve_keys: set[tuple[str, int]] = set()
    for index, item in enumerate(response["preserve"]):
        if not isinstance(item, dict) or set(item) != {"citation", "reason"}:
            failures.append(f"{path.name}: preserve[{index}] has invalid shape")
            continue
        key = citation_key(item["citation"], lines, f"{path.name} preserve[{index}]", failures)
        if key:
            preserve_keys.add(key)
    for required in answer["required_preserve"]:
        key = (required["path"], required["line"])
        if key not in preserve_keys:
            failures.append(f"{path.name}: missing preservation citation {key}")

    action_kinds: set[str] = set()
    for index, action in enumerate(response["actions"]):
        if not isinstance(action, dict) or set(action) != {"id", "kind", "citations", "recommendation"}:
            failures.append(f"{path.name}: actions[{index}] has invalid shape")
            continue
        action_kinds.add(action["kind"])
        if action["kind"] not in {"edit", "repair_link", "clarify"} or not action["citations"]:
            failures.append(f"{path.name}: actions[{index}] has invalid kind or no citations")
        for citation in action["citations"]:
            citation_key(citation, lines, f"{path.name} actions[{index}]", failures)
    for kind in answer["required_action_kinds"]:
        if kind not in action_kinds:
            failures.append(f"{path.name}: missing required action kind {kind}")
    if answer["require_no_patches"] and response["actions"]:
        failures.append(f"{path.name}: clean/no-op case must not recommend actions")

    changed_lines = 0
    for index, patch in enumerate(response["patches"]):
        if not isinstance(patch, dict) or set(patch) != {"path", "rationale", "edits"}:
            failures.append(f"{path.name}: patches[{index}] has invalid shape")
            continue
        if patch["path"] not in answer["allowed_patch_paths"] or not isinstance(patch["edits"], list):
            failures.append(f"{path.name}: patches[{index}] targets a disallowed path or has invalid edits")
            continue
        file_line_count = sum(1 for key in lines if key[0] == patch["path"])
        for edit in patch["edits"]:
            if not isinstance(edit, dict) or set(edit) != {"start_line", "end_line", "replacement"}:
                failures.append(f"{path.name}: patch edit has invalid shape")
                continue
            start, end, replacement = edit["start_line"], edit["end_line"], edit["replacement"]
            if not isinstance(start, int) or not isinstance(end, int) or not isinstance(replacement, str):
                failures.append(f"{path.name}: patch edit has invalid values")
                continue
            if start < 1 or end < start or end > file_line_count:
                failures.append(f"{path.name}: patch edit is outside supplied file lines")
                continue
            protected = {(item["path"], item["line"]) for item in answer["required_preserve"]}
            if any((patch["path"], number) in protected for number in range(start, end + 1)):
                failures.append(f"{path.name}: patch touches a required preserved line")
            action_lines = {(cite.get("path"), cite.get("line")) for action in response["actions"]
                            if isinstance(action, dict) and isinstance(action.get("citations"), list)
                            for cite in action["citations"] if isinstance(cite, dict)}
            if not any((patch["path"], number) in action_lines for number in range(start, end + 1)):
                failures.append(f"{path.name}: patch is not tied to an action citation")
            replacement_lines = len(replacement.splitlines()) if replacement else 0
            changed_lines += max(end - start + 1, replacement_lines)
    if answer["require_no_patches"] and response["patches"]:
        failures.append(f"{path.name}: case requires no proposed patch")
    if not answer["require_no_patches"] and not response["patches"]:
        failures.append(f"{path.name}: findings require a proposed patch")
    if changed_lines > answer["max_patch_changed_lines"]:
        failures.append(
            f"{path.name}: proposed patch changes {changed_lines} lines; maximum is {answer['max_patch_changed_lines']}"
        )

    if not all(isinstance(item, str) for item in response["uncertainties"]):
        failures.append(f"{path.name}: uncertainties must contain strings")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-inputs", action="store_true", help="regenerate the four derived evaluation packets")
    parser.add_argument("--evidence", action="append", type=Path, default=[], help="validate a model response JSON file")
    args = parser.parse_args()

    failures = validate_package(args.write_inputs)
    evidence_paths = list(args.evidence)
    if not evidence_paths and RESULTS.is_dir():
        evidence_paths = sorted(RESULTS.glob("*.json"))
    for evidence_path in evidence_paths:
        failures.extend(validate_evidence(evidence_path.resolve()))

    receipt_path = ROOT / "tests" / "evidence" / "receipts.json"
    if not args.write_inputs and not args.evidence and receipt_path.is_file():
        receipts = load_json(receipt_path)
        if {item["case"] for item in receipts} != set(CASE_IDS):
            failures.append("receipt cases differ from the four declared cases")
        for item in receipts:
            for field, file in (("input_sha256", INPUTS / (item["case"] + ".md")),
                                ("output_sha256", RESULTS / (item["case"] + ".json"))):
                if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != item[field]:
                    failures.append(f"{item['case']}: {field} differs from recorded trial")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    evidence_note = f"; validated {len(evidence_paths)} evidence file(s)" if evidence_paths else ""
    print(f"PASS: Instruction Audit package and four evaluation packets{evidence_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
