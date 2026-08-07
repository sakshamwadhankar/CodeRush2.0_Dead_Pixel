# Dockerfile for Air-Gapped Code Execution Sandbox
FROM python:3.12-slim

# Create a non-root group and user
RUN groupadd -r sandboxgroup && useradd -r -g sandboxgroup -u 1000 -m sandboxuser

# Create workspace directory with appropriate ownership
WORKDIR /workspace
RUN chown -R sandboxuser:sandboxgroup /workspace

# Environment setup
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-privileged user
USER sandboxuser

CMD ["python3"]
