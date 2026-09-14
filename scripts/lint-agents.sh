#!/usr/bin/env bash
#
# Validates agent markdown files:
#   1. YAML frontmatter must exist with name, description, color (ERROR)
#   2. Recommended sections checked but only warned (WARN)
#   3. File must have meaningful content
#
# Usage: ./scripts/lint-agents.sh [file ...]
#   If no files given, scans all agent directories from divisions.json.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=lib.sh
. "$SCRIPT_DIR/lib.sh"
cd "$REPO_ROOT"

REQUIRED_FRONTMATTER=("name" "description" "color")
RECOMMENDED_SECTIONS=("Identity" "Core Mission" "Critical Rules")

errors=0
warnings=0

classify_header_target() {
  local header_lower="$1"

  if [[ "$header_lower" =~ identity ]] ||
     [[ "$header_lower" =~ learning.*memory ]] ||
     [[ "$header_lower" =~ communication ]] ||
     [[ "$header_lower" =~ style ]] ||
     [[ "$header_lower" =~ critical.rule ]] ||
     [[ "$header_lower" =~ rules.you.must.follow ]]; then
    printf 'soul'
  else
    printf 'agents'
  fi
}

frontmatter_field_present() {
  case "$1" in
    name)        (( AGENT_HAS_NAME )) ;;
    description) (( AGENT_HAS_DESCRIPTION )) ;;
    color)       (( AGENT_HAS_COLOR )) ;;
    *)           return 1 ;;
  esac
}

lint_file() {
  local file="$1"

  if [[ ! -f "$file" ]]; then
    echo "ERROR $file: not a file or does not exist"
    errors=$((errors + 1))
    return
  fi

  # 0. Reject CRLF line endings (repo standard is LF — see .gitattributes).
  if LC_ALL=C grep -q $'\r' "$file"; then
    echo "ERROR $file: CRLF line endings detected — convert to LF (e.g. 'perl -i -pe \"s/\\r\$//\" $file'); repo uses LF per .gitattributes"
    errors=$((errors + 1))
    return
  fi

  # 1. Parse frontmatter and body once with the same semantics used by convert.sh.
  if ! load_agent "$file"; then
    echo "ERROR $file: missing or malformed frontmatter delimiters"
    errors=$((errors + 1))
    return
  fi

  # 2. Check required frontmatter fields.
  local field
  for field in "${REQUIRED_FRONTMATTER[@]}"; do
    if ! frontmatter_field_present "$field"; then
      echo "ERROR $file: missing frontmatter field '${field}'"
      errors=$((errors + 1))
    fi
  done

  # 3. Check recommended sections (warn only).
  local body="$AGENT_BODY"
  for section in "${RECOMMENDED_SECTIONS[@]}"; do
    if ! grep -qi -- "$section" <<<"$body"; then
      echo "WARN  $file: missing recommended section '${section}'"
      warnings=$((warnings + 1))
    fi
  done

  # 4. Check file has meaningful content (awk strips wc's leading whitespace on macOS/BSD).
  local word_count
  word_count=$(echo "$body" | wc -w | awk '{print $1}')
  if [[ "${word_count:-0}" -lt 50 ]]; then
    echo "WARN  $file: body seems very short (< 50 words)"
    warnings=$((warnings + 1))
  fi

  local soul_headers=0
  local agents_headers=0
  local fence_marker="" fence_len=0 fence_indent=0
  while IFS= read -r line; do
    # Skip fenced code blocks so ## doc-comment lines (e.g. GDScript `##`)
    # and in-fence markdown headers aren't miscounted (issue #849).
    if [[ -n "$fence_marker" ]]; then
      if fence_closes_p "$line" "$fence_marker" "$fence_len" "$fence_indent"; then
        fence_marker=""
        fence_len=0
        fence_indent=0
      fi
      continue
    fi
    if fence_open_p "$line"; then
      fence_marker="${BASH_REMATCH[2]:0:1}"
      fence_len=${#BASH_REMATCH[2]}
      fence_indent=${#BASH_REMATCH[1]}
      continue
    fi
    if [[ "$line" =~ ^##[[:space:]] ]]; then
      local header_lower
      header_lower=$(printf '%s' "$line" | tr '[:upper:]' '[:lower:]')
      local target
      target=$(classify_header_target "$header_lower")
      if [[ "$target" == "soul" ]]; then
        soul_headers=$((soul_headers + 1))
      else
        agents_headers=$((agents_headers + 1))
      fi
    fi
  done <<< "$body"

  if [[ $soul_headers -eq 0 ]]; then
    echo "WARN  $file: no section headers map to SOUL.md in convert.sh"
    warnings=$((warnings + 1))
  fi

  if [[ $agents_headers -eq 0 ]]; then
    echo "WARN  $file: no section headers map to AGENTS.md in convert.sh"
    warnings=$((warnings + 1))
  fi
}

# Collect files to lint.
files=()
if [[ $# -gt 0 ]]; then
  files=("$@")
else
  divisions="$(python3 "$SCRIPT_DIR/registry.py" divisions "$REPO_ROOT/divisions.json")" || exit 1
  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    if [[ -d "$dir" ]]; then
      while IFS= read -r f; do
        files+=("$f")
      done < <(find "$dir" -name "*.md" -type f ! -name "README.md" | sort)
    fi
  done <<< "$divisions"
fi

if [[ ${#files[@]} -eq 0 ]]; then
  echo "No agent files found."
  exit 1
fi

echo "Linting ${#files[@]} agent files..."
echo ""

for file in "${files[@]}"; do
  lint_file "$file"
done

echo ""
echo "Results: ${errors} error(s), ${warnings} warning(s) in ${#files[@]} files."

if [[ $errors -gt 0 ]]; then
  echo "FAILED: fix the errors above before merging."
  exit 1
else
  echo "PASSED"
  exit 0
fi
