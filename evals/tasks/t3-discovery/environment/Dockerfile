FROM node:22-trixie-slim
ARG CLAUDE_CODE_VERSION=2.1.284
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv git curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}
RUN git config --system user.name eval && git config --system user.email eval@example.invalid \
    && git config --system init.defaultBranch main
# The project: a file:// bare repo with one commit.
RUN git init -q /tmp/demo && cd /tmp/demo \
    && printf 'def add(a, b):\n    return a + b\n' > calc.py && printf '# demo\n' > README.md \
    && git add . && git commit -qm "init" && git clone -q --bare /tmp/demo /srv/demo.git && rm -rf /tmp/demo
WORKDIR /root
# The lib, last (ADR 0217): the harness writes lib/ per run.
COPY lib/ /lib/
# pip and uv resolve from this wheelhouse only: whatever route installs dadaia-workspace gets the run's build.
RUN python3 -m venv /tmp/b && /tmp/b/bin/pip wheel -q -r /lib/requirements.txt uv -w /opt/wheelhouse && rm -rf /tmp/b
ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/wheelhouse UV_NO_INDEX=1 UV_FIND_LINKS=/opt/wheelhouse
