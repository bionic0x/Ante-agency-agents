#!/usr/bin/env bash
#
# convert.sh — Convert agency agent .md files into tool-specific formats.
#
# Reads all agent files from the standard category directories and outputs
# converted files to integrations/<tool>/. Run this to regenerate all
# integration files after adding or modifying agents.
#
# Usage:
#   ./scripts/convert.sh [--tool <name>] [--out <dir>] [--source <agent.md>] [--force-full] [--parallel] [--jobs N] [--help]
#
# Tools:
#   antigravity  — Antigravity skill files (~/.gemini/config/skills/)
#   gemini-cli   — Gemini CLI subagent files (~/.gemini/agents/*.md)
#   opencode     — OpenCode agent files (.opencode/agents/*.md)
#   cursor       — Cursor rule files (.cursor/rules/*.mdc)
#   aider        — Single CONVENTIONS.md for Aider
#   windsurf     — Single .windsurfrules for Windsurf
#   openclaw     — OpenClaw workspaces (integrations/openclaw/<agent>/SOUL.md)
#   qwen         — Qwen Code SubAgent files (~/.qwen/agents/*.md)
#   zcode        — ZCode agent files (.zcode/agents/*.md · ~/.config/zcode/agents/*.md)
#   kimi         — Kimi Code CLI agent files (~/.config/kimi/agents/)
#   codex        — Codex custom agent TOML files (~/.codex/agents/*.toml)
#   osaurus      — Osaurus skill files (~/.osaurus/skills/<name>/SKILL.md)
#   hermes       — Hermes lazy-router plugin (one plugin + on-disk agent index)
#   vibe         — Mistral Vibe agent TOML + prompt files (~/.vibe/agents/*.toml + ~/.vibe/prompts/*.md)
#   all          — All tools (default)
#
# Output is written to integrations/<tool>/ relative to the repo root.
# This script never touches user config dirs — see install.sh for that.
#
#   --source FILE    Convert one canonical source agent without cleaning other outputs.
#                    Requires one per-agent --tool; used by integration-state incremental sync.
#   --force-full     Bypass incremental state and perform the historical clean rebuild.
#   --parallel       When tool is 'all', run independent tools in parallel (output order may vary).
#   --jobs N         Max parallel jobs when using --parallel (default: nproc or 4).

set -euo pipefail

if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; RED=$'\033[0;31m'; BOLD=$'\033[1m'; RESET=$'\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; BOLD=''; RESET=''
fi

info()    { printf "${GREEN}[OK]${RESET}  %s\n" "$*"; }
warn()    { printf "${YELLOW}[!!]${RESET}  %s\n" "$*"; }
error()   { printf "${RED}[ERR]${RESET} %s\n" "$*" >&2; }
header()  { echo -e "\n${BOLD}$*${RESET}"; }

progress_bar() {
  local current="$1" total="$2" width="${3:-20}" i filled empty
  (( total > 0 )) || return
  filled=$(( width * current / total ))
  empty=$(( width - filled ))
  printf "\r  ["
  for (( i=0; i<filled; i++ )); do printf "="; done
  if (( filled < width )); then printf ">"; (( empty-- )); fi
  for (( i=0; i<empty; i++ )); do printf " "; done
  printf "] %s/%s" "$current" "$total"
  [[ -t 1 ]] || printf "\n"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$REPO_ROOT/integrations"
TODAY="$(date +%Y-%m-%d)"

# shellcheck source=lib.sh
. "$SCRIPT_DIR/lib.sh"

usage() {
  sed -n '3,33p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

parallel_jobs_default() {
  local n
  n=$(nproc 2>/dev/null) && [[ -n "$n" ]] && echo "$n" && return
  n=$(sysctl -n hw.ncpu 2>/dev/null) && [[ -n "$n" ]] && echo "$n" && return
  echo 4
}

toml_escape_string() {
  printf '%s' "$1" | perl -0pe '
    s/\\/\\\\/g;
    s/"/\\"/g;
    s/\n/\\n/g;
    s/\r/\\r/g;
    s/\t/\\t/g;
    s/\f/\\f/g;
    s/\x08/\\b/g;
    s/([\x00-\x07\x0B\x0E-\x1F\x7F])/sprintf("\\u%04X", ord($1))/ge;
  '
}

yaml_quote() {
  printf "'%s'" "$(printf '%s' "$1" | sed "s/'/''/g")"
}

convert_antigravity() {
  local file="$1" name description slug outdir outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="agency-$(slugify "$name")"
  body="$(get_body "$file")"
  outdir="$OUT_DIR/antigravity/$slug"
  outfile="$outdir/SKILL.md"
  mkdir -p "$outdir"
  cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
---
${body}
HEREDOC
}

convert_osaurus() {
  local file="$1" name description slug outdir outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="agency-$(slugify "$name")"
  body="$(get_body "$file")"
  outdir="$OUT_DIR/osaurus/$slug"
  outfile="$outdir/SKILL.md"
  mkdir -p "$outdir"
  cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
---
${body}
HEREDOC
}

convert_codex() {
  local file="$1" name description slug outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"
  body="$(get_body "$file")"
  outfile="$OUT_DIR/codex/agents/${slug}.toml"
  mkdir -p "$(dirname "$outfile")"
  cat > "$outfile" <<HEREDOC
name = "$(toml_escape_string "$name")"
description = "$(toml_escape_string "$description")"
developer_instructions = "$(toml_escape_string "$body")"
HEREDOC
}

convert_gemini_cli() {
  local file="$1" name description slug outdir outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"
  body="$(get_body "$file")"
  outdir="$OUT_DIR/gemini-cli/agents"
  outfile="$outdir/${slug}.md"
  mkdir -p "$outdir"
  cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
---
${body}
HEREDOC
}

resolve_opencode_color() {
  local c="$1" mapped
  c="$(printf '%s' "$c" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | tr '[:upper:]' '[:lower:]')"
  case "$c" in
    cyan) mapped="#00FFFF" ;; blue) mapped="#3498DB" ;; green) mapped="#2ECC71" ;;
    red) mapped="#E74C3C" ;; purple) mapped="#9B59B6" ;; orange) mapped="#F39C12" ;;
    teal) mapped="#008080" ;; indigo) mapped="#6366F1" ;; pink) mapped="#E84393" ;;
    gold) mapped="#EAB308" ;; amber) mapped="#F59E0B" ;; neon-green) mapped="#10B981" ;;
    neon-cyan) mapped="#06B6D4" ;; metallic-blue) mapped="#3B82F6" ;; yellow) mapped="#EAB308" ;;
    violet) mapped="#8B5CF6" ;; rose) mapped="#F43F5E" ;; lime) mapped="#84CC16" ;;
    gray) mapped="#6B7280" ;; fuchsia) mapped="#D946EF" ;; *) mapped="$c" ;;
  esac
  if [[ "$mapped" =~ ^#[0-9a-fA-F]{6}$ ]]; then
    printf '#%s\n' "$(printf '%s' "${mapped#\#}" | tr '[:lower:]' '[:upper:]')"; return
  fi
  if [[ "$mapped" =~ ^[0-9a-fA-F]{6}$ ]]; then
    printf '#%s\n' "$(printf '%s' "$mapped" | tr '[:lower:]' '[:upper:]')"; return
  fi
  printf '#6B7280\n'
}

convert_opencode() {
  local file="$1" name description color slug outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  color="$(resolve_opencode_color "$(get_field "color" "$file")")"
  slug="$(slugify "$name")"
  body="$(get_body "$file")"
  outfile="$OUT_DIR/opencode/agents/${slug}.md"
  mkdir -p "$OUT_DIR/opencode/agents"
  cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$name")
description: $(yaml_quote "$description")
mode: subagent
color: '${color}'
---
${body}
HEREDOC
}

convert_cursor() {
  local file="$1" name description slug outfile body
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"
  body="$(get_body "$file")"
  outfile="$OUT_DIR/cursor/rules/${slug}.mdc"
  mkdir -p "$OUT_DIR/cursor/rules"
  cat > "$outfile" <<HEREDOC
---
description: $(yaml_quote "$description")
globs: ""
alwaysApply: false
---
${body}
HEREDOC
}

convert_openclaw() {
  local file="$1" name description slug outdir body
  local soul_content="" agents_content=""
  name="$(get_field "name" "$file")"
  description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"
  body="$(get_body "$file")"
  outdir="$OUT_DIR/openclaw/$slug"
  mkdir -p "$outdir"

  local current_target="agents" current_section=""
  local fence_marker="" fence_len=0 fence_indent=0
  while IFS= read -r line; do
    if [[ -n "$fence_marker" ]]; then
      current_section+="$line"$'\n'
      if fence_closes_p "$line" "$fence_marker" "$fence_len" "$fence_indent"; then
        fence_marker=""; fence_len=0; fence_indent=0
      fi
      continue
    fi
    if fence_open_p "$line"; then
      fence_marker="${BASH_REMATCH[2]:0:1}"
      fence_len=${#BASH_REMATCH[2]}
      fence_indent=${#BASH_REMATCH[1]}
      current_section+="$line"$'\n'
      continue
    fi
    if [[ "$line" =~ ^##[[:space:]] ]]; then
      if [[ -n "$current_section" ]]; then
        if [[ "$current_target" == "soul" ]]; then soul_content+="$current_section"; else agents_content+="$current_section"; fi
      fi
      current_section=""
      local header_lower
      header_lower="$(echo "$line" | tr '[:upper:]' '[:lower:]')"
      if [[ "$header_lower" =~ identity ]] || [[ "$header_lower" =~ learning.*memory ]] ||
         [[ "$header_lower" =~ communication ]] || [[ "$header_lower" =~ style ]] ||
         [[ "$header_lower" =~ critical.rule ]] || [[ "$header_lower" =~ rules.you.must.follow ]]; then
        current_target="soul"
      else
        current_target="agents"
      fi
    fi
    current_section+="$line"$'\n'
  done <<< "$body"
  if [[ -n "$current_section" ]]; then
    if [[ "$current_target" == "soul" ]]; then soul_content+="$current_section"; else agents_content+="$current_section"; fi
  fi

  cat > "$outdir/SOUL.md" <<HEREDOC
${soul_content}
HEREDOC
  cat > "$outdir/AGENTS.md" <<HEREDOC
${agents_content}
HEREDOC

  local emoji vibe
  emoji="$(get_field "emoji" "$file")"
  vibe="$(get_field "vibe" "$file")"
  if [[ -n "$emoji" && -n "$vibe" ]]; then
    cat > "$outdir/IDENTITY.md" <<HEREDOC
# ${emoji} ${name}
${vibe}
HEREDOC
  else
    cat > "$outdir/IDENTITY.md" <<HEREDOC
# ${name}
${description}
HEREDOC
  fi
}

convert_qwen() {
  local file="$1" name description tools slug outfile body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"
  tools="$(get_field "tools" "$file")"; slug="$(slugify "$name")"; body="$(get_body "$file")"
  outfile="$OUT_DIR/qwen/agents/${slug}.md"; mkdir -p "$(dirname "$outfile")"
  if [[ -n "$tools" ]]; then
    cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
tools: $(yaml_quote "$tools")
---
${body}
HEREDOC
  else
    cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
---
${body}
HEREDOC
  fi
}

convert_zcode() {
  local file="$1" name description tools slug outfile body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"
  tools="$(get_field "tools" "$file")"; slug="$(slugify "$name")"; body="$(get_body "$file")"
  outfile="$OUT_DIR/zcode/agents/${slug}.md"; mkdir -p "$(dirname "$outfile")"
  if [[ -n "$tools" ]]; then
    cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
tools: $(yaml_quote "$tools")
---
${body}
HEREDOC
  else
    cat > "$outfile" <<HEREDOC
---
name: $(yaml_quote "$slug")
description: $(yaml_quote "$description")
---
${body}
HEREDOC
  fi
}

convert_kimi() {
  local file="$1" name description slug outdir agent_file body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"; body="$(get_body "$file")"
  outdir="$OUT_DIR/kimi/$slug"; agent_file="$outdir/agent.yaml"; mkdir -p "$outdir"
  cat > "$agent_file" <<HEREDOC
version: 1
agent:
  name: ${slug}
  extend: default
  system_prompt_path: ./system.md
HEREDOC
  cat > "$outdir/system.md" <<HEREDOC
# ${name}

${description}

${body}
HEREDOC
}

convert_vibe() {
  local file="$1" name description slug outdir agent_file prompt_file body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"
  slug="$(slugify "$name")"; body="$(get_body "$file")"; outdir="$OUT_DIR/vibe"
  agent_file="$outdir/agents/${slug}.toml"; prompt_file="$outdir/prompts/${slug}.md"
  mkdir -p "$outdir/agents" "$outdir/prompts"
  cat > "$agent_file" <<HEREDOC
agent_type = "agent"
system_prompt_id = "${slug}"
HEREDOC
  cat > "$prompt_file" <<HEREDOC
# ${name}

${description}

${body}
HEREDOC
}

AIDER_TMP="$(mktemp)"
WINDSURF_TMP="$(mktemp)"
trap 'rm -f "$AIDER_TMP" "$WINDSURF_TMP"' EXIT

cat > "$AIDER_TMP" <<'HEREDOC'
# The Agency — AI Agent Conventions
#
# This file provides Aider with the full roster of specialized AI agents from
# The Agency (https://github.com/msitarzewski/agency-agents).
#
# To activate an agent, reference it by name in your Aider session prompt, e.g.:
#   "Use the Frontend Developer agent to review this component."
#
# Generated by scripts/convert.sh — do not edit manually.

HEREDOC

cat > "$WINDSURF_TMP" <<'HEREDOC'
# The Agency — AI Agent Rules for Windsurf
#
# Full roster of specialized AI agents from The Agency.
# To activate an agent, reference it by name in your Windsurf conversation.
#
# Generated by scripts/convert.sh — do not edit manually.

HEREDOC

accumulate_aider() {
  local file="$1" name description body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"; body="$(get_body "$file")"
  cat >> "$AIDER_TMP" <<HEREDOC

---

## ${name}

> ${description}

${body}
HEREDOC
}

accumulate_windsurf() {
  local file="$1" name description body
  name="$(get_field "name" "$file")"; description="$(get_field "description" "$file")"; body="$(get_body "$file")"
  cat >> "$WINDSURF_TMP" <<HEREDOC

================================================================================
## ${name}
${description}
================================================================================

${body}

HEREDOC
}

clean_tool_output() {
  [[ "$1" =~ ^[a-z0-9-]+$ ]] || { echo "ERROR: clean_tool_output: refusing non-slug tool name '$1'" >&2; return 1; }
  local dir="$OUT_DIR/$1"
  [[ -d "$dir" ]] || return 0
  find "$dir" -mindepth 1 -maxdepth 1 ! -name 'README.md' -exec rm -rf {} +
}

convert_one_source() {
  local tool="$1" source="$2" rel="" divisions d allowed=false source_dir
  [[ "$tool" != "aider" && "$tool" != "windsurf" && "$tool" != "hermes" ]] || {
    error "--source is only valid for per-agent converter tools (not $tool)"; return 1;
  }

  if [[ "$source" != /* ]]; then source="$REPO_ROOT/$source"; fi
  [[ -f "$source" ]] || { error "--source does not exist: $source"; return 1; }
  source_dir="$(cd "$(dirname "$source")" && pwd -P)" || return 1
  source="$source_dir/$(basename "$source")"
  [[ "$source" == "$REPO_ROOT/"* ]] || { error "--source must be inside the repository"; return 1; }
  rel="${source#"$REPO_ROOT/"}"

  divisions="$(python3 "$SCRIPT_DIR/registry.py" divisions "$REPO_ROOT/divisions.json")" || return 1
  while IFS= read -r d; do
    [[ -n "$d" ]] || continue
    if [[ "$rel" == "$d/"* ]]; then allowed=true; break; fi
  done <<< "$divisions"
  $allowed || { error "--source is not inside a registered division: $rel"; return 1; }

  load_agent "$source" || { error "--source is not an agent file: $rel"; return 1; }
  [[ -n "$AGENT_NAME" ]] || { error "--source has no name frontmatter: $rel"; return 1; }

  case "$tool" in
    antigravity) convert_antigravity "$source" ;; codex) convert_codex "$source" ;;
    gemini-cli) convert_gemini_cli "$source" ;; opencode) convert_opencode "$source" ;;
    cursor) convert_cursor "$source" ;; openclaw) convert_openclaw "$source" ;;
    qwen) convert_qwen "$source" ;; zcode) convert_zcode "$source" ;; kimi) convert_kimi "$source" ;;
    osaurus) convert_osaurus "$source" ;; vibe) convert_vibe "$source" ;;
    *) error "--source unsupported for tool '$tool'"; return 1 ;;
  esac
}

run_conversions() {
  local tool="$1" source="${2:-}" count=0 divisions
  if [[ -n "$source" ]]; then convert_one_source "$tool" "$source" || return 1; echo 1; return 0; fi
  if [[ "$tool" == "hermes" ]]; then
    clean_tool_output "$tool"
    python3 "$SCRIPT_DIR/build-hermes-plugin.py" --repo-root "$REPO_ROOT" --out "$OUT_DIR/hermes"
    return
  fi
  clean_tool_output "$tool"
  divisions="$(python3 "$SCRIPT_DIR/registry.py" divisions "$REPO_ROOT/divisions.json")" || return 1
  while IFS= read -r dir; do
    [[ -n "$dir" ]] || continue
    local dirpath="$REPO_ROOT/$dir"
    [[ -d "$dirpath" ]] || continue
    while IFS= read -r -d '' file; do
      load_agent "$file" || continue
      [[ -n "$AGENT_NAME" ]] || continue
      case "$tool" in
        antigravity) convert_antigravity "$file" ;; codex) convert_codex "$file" ;;
        gemini-cli) convert_gemini_cli "$file" ;; opencode) convert_opencode "$file" ;;
        cursor) convert_cursor "$file" ;; openclaw) convert_openclaw "$file" ;;
        qwen) convert_qwen "$file" ;; zcode) convert_zcode "$file" ;; kimi) convert_kimi "$file" ;;
        osaurus) convert_osaurus "$file" ;; vibe) convert_vibe "$file" ;;
        aider) accumulate_aider "$file" ;; windsurf) accumulate_windsurf "$file" ;;
      esac || return 1
      (( count++ )) || true
    done < <(find "$dirpath" -name "*.md" -type f -print0 | sort -z)
  done <<< "$divisions"
  echo "$count"
}

main() {
  local tool="all" source="" force_full=false use_parallel=false parallel_jobs
  parallel_jobs="$(parallel_jobs_default)"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tool) tool="${2:?'--tool requires a value'}"; shift 2 ;;
      --out) OUT_DIR="${2:?'--out requires a value'}"; shift 2 ;;
      --source) source="${2:?'--source requires a value'}"; shift 2 ;;
      --force-full) force_full=true; shift ;;
      --parallel) use_parallel=true; shift ;;
      --jobs) parallel_jobs="${2:?'--jobs requires a value'}"; shift 2 ;;
      --help|-h) usage ;;
      *) error "Unknown option: $1"; exit 1 ;;
    esac
  done

  [[ "$parallel_jobs" =~ ^[1-9][0-9]*$ ]] || { error "--jobs must be a positive integer"; exit 1; }
  local valid_tools=("antigravity" "gemini-cli" "opencode" "cursor" "aider" "windsurf" "openclaw" "qwen" "zcode" "kimi" "codex" "osaurus" "hermes" "vibe" "all")
  local valid=false
  for t in "${valid_tools[@]}"; do [[ "$t" == "$tool" ]] && valid=true && break; done
  $valid || { error "Unknown tool '$tool'. Valid: ${valid_tools[*]}"; exit 1; }

  if [[ -n "$source" ]]; then
    [[ "$tool" != "all" ]] || { error "--source requires one explicit --tool"; exit 1; }
    ! $use_parallel || { error "--source cannot be combined with --parallel"; exit 1; }
    ! $force_full || { error "--source cannot be combined with --force-full"; exit 1; }
  fi

  # Canonical single-tool conversion is state-aware. Custom --out directories,
  # all-tool builds, --source calls and --force-full retain deterministic direct
  # conversion semantics and never recurse through integration-state.py.
  if [[ -z "$source" && "$tool" != "all" && "$OUT_DIR" == "$REPO_ROOT/integrations" ]] && ! $force_full; then
    command -v python3 >/dev/null 2>&1 || { error "python3 is required for incremental conversion state"; exit 1; }
    python3 "$SCRIPT_DIR/integration-state.py" sync "$tool"
    exit $?
  fi

  header "The Agency -- Converting agents to tool-specific formats"
  echo "  Repo:   $REPO_ROOT"
  echo "  Output: $OUT_DIR"
  echo "  Tool:   $tool"
  [[ -n "$source" ]] && echo "  Source: $source"
  $force_full && echo "  Mode:   full rebuild"
  echo "  Date:   $TODAY"
  if $use_parallel && [[ "$tool" == "all" ]]; then info "Parallel mode: output buffered so each tool's output stays together."; fi

  local tools_to_run=()
  if [[ "$tool" == "all" ]]; then
    tools_to_run=("antigravity" "gemini-cli" "opencode" "cursor" "aider" "windsurf" "openclaw" "qwen" "zcode" "kimi" "codex" "osaurus" "hermes" "vibe")
  else
    tools_to_run=("$tool")
  fi
  local total=0 n_tools=${#tools_to_run[@]}

  if $use_parallel && [[ "$tool" == "all" ]]; then
    local parallel_tools=(antigravity gemini-cli opencode cursor openclaw qwen zcode kimi codex osaurus hermes vibe)
    local parallel_out_dir
    parallel_out_dir="$(mktemp -d)"
    info "Converting: ${#parallel_tools[@]}/${n_tools} tools in parallel (output buffered per tool)..."
    export AGENCY_CONVERT_OUT_DIR="$parallel_out_dir" AGENCY_CONVERT_SCRIPT="$SCRIPT_DIR/convert.sh" AGENCY_CONVERT_OUT="$OUT_DIR"
    printf '%s\n' "${parallel_tools[@]}" | xargs -P "$parallel_jobs" -I {} sh -c '"$AGENCY_CONVERT_SCRIPT" --tool "{}" --out "$AGENCY_CONVERT_OUT" --force-full > "$AGENCY_CONVERT_OUT_DIR/{}" 2>&1'
    for t in "${parallel_tools[@]}"; do [[ -f "$parallel_out_dir/$t" ]] && cat "$parallel_out_dir/$t"; done
    rm -rf "$parallel_out_dir"
    local idx=$(( ${#parallel_tools[@]} + 1 ))
    for t in aider windsurf; do
      progress_bar "$idx" "$n_tools"; printf "\n"; header "Converting: $t ($idx/$n_tools)"
      local count; count="$(run_conversions "$t")" || return 1
      total=$(( total + count )); info "Converted $count agents for $t"; (( idx++ )) || true
    done
  else
    local i=0
    for t in "${tools_to_run[@]}"; do
      (( i++ )) || true; progress_bar "$i" "$n_tools"; printf "\n"; header "Converting: $t ($i/$n_tools)"
      local count; count="$(run_conversions "$t" "$source")" || return 1
      total=$(( total + count )); info "Converted $count agents for $t"
    done
  fi

  if [[ -z "$source" && ( "$tool" == "all" || "$tool" == "aider" ) ]]; then
    mkdir -p "$OUT_DIR/aider"; cp "$AIDER_TMP" "$OUT_DIR/aider/CONVENTIONS.md"; info "Wrote integrations/aider/CONVENTIONS.md"
  fi
  if [[ -z "$source" && ( "$tool" == "all" || "$tool" == "windsurf" ) ]]; then
    mkdir -p "$OUT_DIR/windsurf"; cp "$WINDSURF_TMP" "$OUT_DIR/windsurf/.windsurfrules"; info "Wrote integrations/windsurf/.windsurfrules"
  fi

  echo ""
  if $use_parallel && [[ "$tool" == "all" ]]; then info "Done. $n_tools tools (parallel; total conversions not aggregated)."; else info "Done. Total conversions: $total"; fi
}

main "$@"
