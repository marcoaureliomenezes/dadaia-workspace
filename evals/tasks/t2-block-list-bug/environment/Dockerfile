FROM node:22-trixie-slim
ARG CLAUDE_CODE_VERSION=2.1.284
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
RUN git config --system user.name eval && git config --system user.email eval@example.invalid \
    && git config --system init.defaultBranch main
COPY project.sh /opt/eval/project.sh
WORKDIR /workspace
# The lib, last (ADR 0217): the harness writes lib/ per run.
COPY lib/ /lib/
RUN python3 -m venv /opt/dadaia && /opt/dadaia/bin/pip install -q --no-cache-dir -r /lib/requirements.txt \
    && ln -s /opt/dadaia/bin/dadaia /opt/dadaia/bin/dadaia-workspace /usr/local/bin/ \
    && bash /opt/eval/project.sh
