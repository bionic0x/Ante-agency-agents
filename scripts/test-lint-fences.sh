#!/usr/bin/env bash
# Code fences that GitHub renders differently from what the author meant must
# fail lint, and the fix the error message suggests must pass it.
#
# Markdown has no nesting at equal fence length. Inside a ```markdown template,
# a ```bash line is text, and the example's closing ``` ends the template, so
# the rest of it renders as headings and prose. Seven roster agents shipped
# that way, three of them with the last block left open to the end of the file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIXTURE="$(mktemp -d "${TMPDIR:-/tmp}/agency-lint-fences.XXXXXX")"
trap 'rm -rf "$FIXTURE"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

frontmatter() {
  cat <<'EOF'
---
name: Fence Fixture
description: Fixture agent for the code-fence lint rules
color: blue
---
## Identity
Enough words to clear the short-body warning, repeated so the linter has a
body to read: this fixture exists to check how fenced code blocks are parsed.
## Core Mission
Show a template that contains a code example.
## Critical Rules
Keep fences balanced.
EOF
}

# 1. ```bash inside ```markdown: the inner fence does not nest.
{ frontmatter; cat <<'EOF'
### Template
```markdown
# Report
```bash
npm test
```
## Findings
```
EOF
} > "$FIXTURE/nested.md"
if bash "$SCRIPT_DIR/lint-agents.sh" "$FIXTURE/nested.md" > "$FIXTURE/nested.log" 2>&1; then
  fail "linter accepted a \`\`\`bash fence nested in a \`\`\`markdown block of the same length"
fi
grep -Fq "nested.md:16: '\`\`\`bash' inside the block opened at line 14 does not nest" "$FIXTURE/nested.log" \
  || { cat "$FIXTURE/nested.log" >&2; fail "nested-fence error is missing or names the wrong lines"; }

# 2. A block left open to the end of the file.
{ frontmatter; printf '%s\n' '### Layout' '```' 'css/' 'js/'; } > "$FIXTURE/unclosed.md"
if bash "$SCRIPT_DIR/lint-agents.sh" "$FIXTURE/unclosed.md" > "$FIXTURE/unclosed.log" 2>&1; then
  fail "linter accepted a code block that is never closed"
fi
grep -Fq "unclosed.md:14: code block is never closed" "$FIXTURE/unclosed.log" \
  || { cat "$FIXTURE/unclosed.log" >&2; fail "unclosed-fence error is missing or names the wrong line"; }

# 3. The fix the message suggests — a longer outer fence — passes, and so do
#    tilde fences and a shorter run inside a longer block.
{ frontmatter; cat <<'EOF'
### Template
````markdown
# Report
```bash
npm test
```
## Findings
````
~~~text
```python is just text in here
~~~
EOF
} > "$FIXTURE/valid.md"
bash "$SCRIPT_DIR/lint-agents.sh" "$FIXTURE/valid.md" > "$FIXTURE/valid.log" 2>&1 \
  || { cat "$FIXTURE/valid.log" >&2; fail "linter rejected correctly nested fences"; }

# 4. The helper itself, which the OpenClaw split in convert.sh shares: only a
#    bare run of the same character, at least as long, closes a block.
. "$SCRIPT_DIR/lib.sh"
fence_closes_p '```python' '`' 3 0 && fail "fence_closes_p treated '\`\`\`python' as a closing fence"
fence_closes_p '```' '`' 3 0       || fail "fence_closes_p rejected a bare closing fence"
fence_closes_p '````  ' '`' 3 0    || fail "fence_closes_p rejected a longer closing fence with trailing spaces"
fence_closes_p '```' '`' 4 0       && fail "fence_closes_p let a shorter run close a longer fence"

echo "PASS: nested and unclosed fences are rejected; correctly nested fences pass"
