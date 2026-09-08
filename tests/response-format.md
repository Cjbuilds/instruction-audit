## Evaluation response format

For this evaluation only, return one JSON object and no surrounding Markdown. Use this exact shape; arrays may be empty. This changes only the response encoding, not the audit method or decisions.

```json
{
  "schema_version": 1,
  "mode": "file_read | pasted_manifest",
  "status": "findings | clean | incomplete",
  "summary": "short factual summary",
  "coverage": [
    {"path": "relative/path", "state": "read | missing | unavailable", "reason": "evidence for this state"}
  ],
  "conflicts": [
    {
      "id": "C1",
      "classification": "conflict | ambiguity",
      "scope": "condition where passages overlap or may overlap",
      "passages": [{"path": "file", "line": 1, "quote": "exact complete line"}],
      "explanation": "why actions are incompatible or meaning is unresolved"
    }
  ],
  "links": [
    {
      "source": {"path": "file", "line": 1, "quote": "exact complete line"},
      "target": "linked/path-or-url",
      "state": "exists | missing | unavailable | external_unchecked",
      "reason": "evidence for this state"
    }
  ],
  "preserve": [
    {"citation": {"path": "file", "line": 1, "quote": "exact complete line"}, "reason": "essential constraint"}
  ],
  "actions": [
    {
      "id": "A1",
      "kind": "edit | repair_link | clarify",
      "citations": [{"path": "file", "line": 1, "quote": "exact complete line"}],
      "recommendation": "smallest action and why"
    }
  ],
  "patches": [
    {
      "path": "file to change",
      "rationale": "problem this resolves",
      "edits": [{"start_line": 1, "end_line": 1, "replacement": "complete replacement text"}]
    }
  ],
  "uncertainties": ["fact that could not be established"]
}
```
