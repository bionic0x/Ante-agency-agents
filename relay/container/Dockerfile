# Reference agent image for NEXUS Relay. Any image works if it provides python3 and the
# command named in runtime.agent_command. The relay supplies the network bridge script,
# the agent profile and the workspace at run time; nothing secret is baked in.
# Base pinned by digest (multi-arch index) and Claude Code pinned by version, so a rebuild
# cannot silently pull different code. Update both deliberately, together.
FROM node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392
ARG CLAUDE_CODE_VERSION=2.1.295

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g --no-audit --no-fund "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}" \
 && npm cache clean --force

# The relay runs the container as the host user's uid; HOME is a tmpfs at run time.
ENV HOME=/tmp \
    DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
WORKDIR /workspace
