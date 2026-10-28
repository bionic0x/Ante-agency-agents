# Time-limited CI dependency risk acceptance

## GHSA-xcq7-p3pf-p88h — expires 2027-01-31

- Scope: the Semgrep tool environment in `semgrep.txt`, not Ante or Relay.
- Owner: repository maintainer; acceptance requested in the PR #62 review.
- Advisory: https://github.com/advisories/GHSA-xcq7-p3pf-p88h.
- The affected API parses inbound W3C `tracestate` headers. The workflow invokes
  `semgrep scan` as a one-shot process without an inbound HTTP listener or server
  instrumentation. This is a deployment-specific reachability assessment, not a
  claim that the dependency is patched or safe in other contexts.
- Controls: `--metrics=off`, version checks disabled, `OTEL_SDK_DISABLED=true`,
  `OTEL_PROPAGATORS=none`; no server mode. Outbound rule downloads are not an
  inbound instrumented HTTP service.
- Upstream constraint: Semgrep 1.179.0 and the reviewed 1.182.1 release require
  OpenTelemetry API/SDK/exporter `~=1.37.0`; the advisory fixes API 1.45.1. No
  unsupported API override is introduced. The existing MCP 1.30.0 pin is retained;
  its separate Semgrep metadata mismatch is not resolved by this exception.
- Reopen immediately if the invocation gains a listener, instrumented request
  handling, untrusted trace-context extraction, another consumer of this lock,
  or a dependency/control change. Remove the exception when compatible patched
  tooling is available. Native OSV expiry re-enables the finding on expiration.

The config is adjacent to the CI requirement locks; no global `--config` override
is used. It ignores one advisory (and its OSV aliases), not a package or severity
class. `certifi` is upgraded, not ignored. A clean scan means no unaccepted
findings under this scoped policy, not absence of vulnerable dependencies.
