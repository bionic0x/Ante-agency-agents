# Reference agent image for NEXUS Relay. Any image works if it provides python3 and the
# command named in runtime.agent_command. The relay supplies the network bridge script,
# the agent profile and the workspace at run time; nothing secret is baked in.
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 git ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code \
 && npm cache clean --force

# The relay runs the container as the host user's uid; HOME is a tmpfs at run time.
ENV HOME=/tmp \
    DISABLE_AUTOUPDATER=1 \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1
WORKDIR /workspace
