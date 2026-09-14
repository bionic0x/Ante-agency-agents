#!/usr/bin/env bash
#
# lib.sh — shared pure-bash helpers for scripts/convert.sh and scripts/install.sh.
#
# No external dependencies. Bash 3.2+ compatible (macOS ships 3.2).
# Sourced, not executed. Groups:
#   1. Frontmatter / slug helpers   (agent data model)
#   2. set -e-safe primitives
#   3. Terminal capability + ANSI    (color, unicode, sizing)
#   4. TUI primitives                (raw input, alt-screen, flicker-free draw)
#
# Everything here is namespaced loosely and guarded so it is safe to source
# from a script already running under `set -euo pipefail`.

# ---------------------------------------------------------------------------
# 1. Frontmatter / slug helpers
# ---------------------------------------------------------------------------

# _emit_yaml_scalar <value> — normalize the small YAML scalar subset used by
# agent frontmatter. This deliberately mirrors the previous awk implementation:
# trim outer padding, strip one matching quote pair, unescape \" / \\ in double
# quotes and doubled apostrophes in single quotes. It is pure bash so repeated
# metadata lookups do not fork awk thousands of times during full conversion.
_emit_yaml_scalar() {
  local v="$1"
  while [[ "$v" == ' '* || "$v" == $'\t'* ]]; do v="${v#?}"; done
  while [[ "$v" == *' ' || "$v" == *$'\t' ]]; do v="${v%?}"; done

  local n=${#v}
  if (( n >= 2 )) && [[ "${v:0:1}" == '"' && "${v:n-1:1}" == '"' ]]; then
    v="${v:1:n-2}"
    v="${v//\\\"/\"}"
    v="${v//\\\\/\\}"
  elif (( n >= 2 )) && [[ "${v:0:1}" == "'" && "${v:n-1:1}" == "'" ]]; then
    v="${v:1:n-2}"
    v="${v//\'\'/\'}"
  fi
  printf '%s\n' "$v"
}

# get_field <field> <file> — value of a YAML frontmatter field (first match).
# Frontmatter is intentionally parsed with bash built-ins: fields live in the
# first --- block; indented non-empty continuation lines are folded with spaces.
get_field() {
  local field="$1" file="$2" line val="" cont
  local fm=0 found=0
  [[ -f "$file" ]] || return 0

  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ "$line" == '---' ]]; then
      fm=$(( fm + 1 ))
      if (( fm == 2 )); then
        (( found )) && _emit_yaml_scalar "$val"
        return 0
      fi
      continue
    fi
    (( fm == 1 )) || continue

    if (( found )); then
      if [[ "$line" == ' '* || "$line" == $'\t'* ]]; then
        cont="$line"
        while [[ "$cont" == ' '* || "$cont" == $'\t'* ]]; do cont="${cont#?}"; done
        if [[ -n "$cont" ]]; then
          val="$val $cont"
          continue
        fi
      fi
      _emit_yaml_scalar "$val"
      return 0
    fi

    case "$line" in
      "$field: "*) val="${line#"$field: "}"; found=1 ;;
    esac
  done < "$file"

  (( found )) && _emit_yaml_scalar "$val"
}

# get_body <file> — file contents with the leading frontmatter block stripped.
# Pure bash avoids one awk process per agent conversion while preserving the
# command-substitution behavior callers already rely on (trailing newlines are
# stripped by $(...) in the caller).
get_body() {
  local line fm=0
  [[ -f "$1" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    if (( fm < 2 )) && [[ "$line" == '---' ]]; then
      fm=$(( fm + 1 ))
      continue
    fi
    (( fm >= 2 )) && printf '%s\n' "$line"
  done < "$1"
}

# slugify <string> — "Frontend Developer" -> "frontend-developer".
# Pure bash keeps this hot-path helper fork-free. The mapping is intentionally
# ASCII-only, matching the prior tr+sed contract: non [a-z0-9] characters become
# separators, repeated separators collapse, and leading/trailing separators drop.
slugify() {
  local s="$1" out="" ch mapped i len=${#1}
  for (( i=0; i<len; i++ )); do
    ch="${s:i:1}"
    case "$ch" in
      [Aa]) mapped=a ;; [Bb]) mapped=b ;; [Cc]) mapped=c ;; [Dd]) mapped=d ;; [Ee]) mapped=e ;;
      [Ff]) mapped=f ;; [Gg]) mapped=g ;; [Hh]) mapped=h ;; [Ii]) mapped=i ;; [Jj]) mapped=j ;;
      [Kk]) mapped=k ;; [Ll]) mapped=l ;; [Mm]) mapped=m ;; [Nn]) mapped=n ;; [Oo]) mapped=o ;;
      [Pp]) mapped=p ;; [Qq]) mapped=q ;; [Rr]) mapped=r ;; [Ss]) mapped=s ;; [Tt]) mapped=t ;;
      [Uu]) mapped=u ;; [Vv]) mapped=v ;; [Ww]) mapped=w ;; [Xx]) mapped=x ;; [Yy]) mapped=y ;;
      [Zz]) mapped=z ;; [0-9]) mapped="$ch" ;; *) mapped=- ;;
    esac
    if [[ "$mapped" == '-' ]]; then
      [[ -n "$out" && "$out" != *- ]] && out="${out}-"
    else
      out="${out}${mapped}"
    fi
  done
  [[ "$out" == *- ]] && out="${out%-}"
  printf '%s' "$out"
}

# agent_slug <file> — slug derived from the file's `name:` frontmatter.
# Single source of truth so convert + install always agree.
agent_slug() {
  local name; name="$(get_field name "$1")"
  [[ -n "$name" ]] && slugify "$name"
}

# is_agent_file <file> — true if the file starts with a YAML frontmatter fence.
is_agent_file() {
  local first=""
  [[ -f "$1" ]] || return 1
  IFS= read -r first < "$1" || true
  [[ "$first" == '---' ]]
}

# ---------------------------------------------------------------------------
# 1b. Markdown fenced-code-block helpers (issue #849)
# ---------------------------------------------------------------------------

# fence_open_p <line> — 0 if <line> opens a fence (3+ ` or ~, 0–3 leading
# spaces); sets BASH_REMATCH[1]=indent, [2]=marker run. Read those directly,
# not via $(), so the per-line convert/lint loops stay subshell-free. Else 1.
fence_open_p() {
  local line="$1"
  local re='^( {0,3})(`{3,}|~{3,})'
  [[ "$line" =~ $re ]]
}

# fence_closes_p <line> <open_marker> <open_len> <open_indent> — 0 if <line>
# closes the open fence (same char, run len >= open, indent <= open); 1
# otherwise, including non-fence lines (callers need not pre-classify).
fence_closes_p() {
  local line="$1" open_marker="$2" open_len="$3" open_indent="$4"
  local re='^( {0,3})(`{3,}|~{3,})'
  [[ "$line" =~ $re ]] || return 1
  local close_indent=${#BASH_REMATCH[1]}
  local close_run="${BASH_REMATCH[2]}"
  [[ "${close_run:0:1}" == "$open_marker" ]] || return 1
  (( ${#close_run} >= open_len )) || return 1
  (( close_indent <= open_indent )) || return 1
  return 0
}

# ---------------------------------------------------------------------------
# 2. set -e-safe primitives  (absorbs #505 — no more `(( x++ )) || true`)
# ---------------------------------------------------------------------------

# incr <varname> — increment a numeric variable in place, safely under set -e.
incr() { printf -v "$1" '%d' "$(( ${!1:-0} + 1 ))"; }

# ---------------------------------------------------------------------------
# 3. Terminal capability + ANSI
# ---------------------------------------------------------------------------

supports_color() { [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; }
supports_unicode() { [[ "${LANG:-}${LC_ALL:-}${LC_CTYPE:-}" == *[Uu][Tt][Ff]* ]]; }

term_cols() { local c; c="$(tput cols 2>/dev/null)"; [[ "$c" =~ ^[0-9]+$ ]] && echo "$c" || echo 80; }
term_rows() { local r; r="$(tput lines 2>/dev/null)"; [[ "$r" =~ ^[0-9]+$ ]] && echo "$r" || echo 24; }

# init_ansi — populate C_* color vars + box-drawing chars (UTF-8 or ASCII).
init_ansi() {
  if supports_color; then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'; C_DIM=$'\033[2m'; C_REV=$'\033[7m'
    C_RED=$'\033[0;31m'; C_GREEN=$'\033[0;32m'; C_YELLOW=$'\033[1;33m'
    C_BLUE=$'\033[0;34m'; C_CYAN=$'\033[0;36m'; C_MAGENTA=$'\033[0;35m'
  else
    C_RESET=''; C_BOLD=''; C_DIM=''; C_REV=''
    C_RED=''; C_GREEN=''; C_YELLOW=''; C_BLUE=''; C_CYAN=''; C_MAGENTA=''
  fi
  if supports_unicode; then
    BX_TL='╭'; BX_TR='╮'; BX_BL='╰'; BX_BR='╯'; BX_H='─'; BX_V='│'
    GLYPH_ON='✓'; GLYPH_DET='●'; GLYPH_OFF='○'; GLYPH_CUR='▸'
  else
    BX_TL='+'; BX_TR='+'; BX_BL='+'; BX_BR='+'; BX_H='-'; BX_V='|'
    GLYPH_ON='x'; GLYPH_DET='*'; GLYPH_OFF=' '; GLYPH_CUR='>'
  fi
}

# repeat <char> <n> — print <char> n times.
repeat() { local i; for (( i=0; i<$2; i++ )); do printf '%s' "$1"; done; }

# strip_ansi <string> — remove ANSI escape sequences (for width math).
strip_ansi() { printf '%s' "$1" | sed $'s/\033\\[[0-9;]*m//g'; }

# vis_len <string> — visible length (ANSI-stripped). Note: assumes 1 col/char.
vis_len() { local s; s="$(strip_ansi "$1")"; printf '%s' "${#s}"; }

# ---------------------------------------------------------------------------
# 4. TUI primitives (used by install.sh's interactive wizard)
# ---------------------------------------------------------------------------

_TUI_ACTIVE=0
_TUI_STTY_SAVE=""

# tui_begin — enter alt screen, hide cursor, raw mode; install restore trap.
tui_begin() {
  # Test hook: drive the wizard from piped keystrokes (skips the TTY gate and
  # the alt-screen/stty takeover). Used by the install-script test harness.
  [[ -n "${AGENCY_TUI_FORCE:-}" ]] && { _TUI_ACTIVE=1; return 0; }
  [[ -t 0 && -t 1 ]] || return 1
  _TUI_STTY_SAVE="$(stty -g 2>/dev/null)" || return 1
  stty -echo -icanon time 0 min 1 2>/dev/null || return 1
  printf '\033[?1049h\033[?25l'   # alt screen + hide cursor
  _TUI_ACTIVE=1
  trap 'tui_end' EXIT INT TERM
}

# tui_end — restore terminal (idempotent; safe from trap).
tui_end() {
  [[ "$_TUI_ACTIVE" == "1" ]] || return 0
  printf '\033[?25h\033[?1049l'   # show cursor + leave alt screen
  [[ -n "$_TUI_STTY_SAVE" ]] && stty "$_TUI_STTY_SAVE" 2>/dev/null
  _TUI_ACTIVE=0
  trap - EXIT INT TERM
}

# read_key — read one keypress, echo a normalized token:
#   UP DOWN LEFT RIGHT ENTER SPACE ESC BACKSPACE TAB  or the literal character.
#
# Reads escape sequences byte-by-byte with INTEGER timeouts (bash 3.2 has no
# fractional -t). A real arrow sends ESC [ A (or ESC O A in application-cursor
# mode) as one buffered burst, so the follow-up reads return instantly; only a
# lone Esc waits out the 1s timeout. Handles both CSI ('[') and SS3 ('O').
read_key() {
  local k k2 k3
  IFS= read -rsn1 k 2>/dev/null || { printf 'EOF'; return; }
  case "$k" in
    $'\033')
      if ! IFS= read -rsn1 -t 1 k2 2>/dev/null; then printf 'ESC'; return; fi
      if [[ "$k2" == '[' || "$k2" == 'O' ]]; then
        IFS= read -rsn1 -t 1 k3 2>/dev/null
        case "$k3" in
          A) printf 'UP' ;;    B) printf 'DOWN' ;;
          C) printf 'RIGHT' ;; D) printf 'LEFT' ;;
          *) printf 'ESC' ;;
        esac
      else
        printf 'ESC'
      fi ;;
    $'\n'|$'\r'|'') printf 'ENTER' ;;   # Enter is CR in raw mode (sometimes empty)
    ' ') printf 'SPACE' ;;
    $'\t') printf 'TAB' ;;
    $'\177'|$'\010') printf 'BACKSPACE' ;;
    *) printf '%s' "$k" ;;
  esac
}

# draw_frame <buffer> — home cursor and paint a pre-composed frame.
# Flicker-free: erase-to-end-of-line (\033[K) on every line so a shorter new
# line never leaves the previous frame's tail behind, then erase-to-end-of-
# screen (\033[0J) to drop any leftover lines below the frame.
draw_frame() {
  local buf="${1//$'\n'/$'\033[K'$'\n'}"
  printf '\033[H%s\033[K\033[0J' "$buf"
}
