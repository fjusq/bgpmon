FROM alpine:3.20

# Install bird2 and tools
RUN apk add --no-cache bird bash coreutils grep

# Prepare config dir
RUN mkdir -p /etc/bird
WORKDIR /app

# Copy template and entrypoint
COPY bird.conf.tmpl /app/bird.conf.tmpl
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Add metrics writer
COPY scripts/bgpmon_write_metrics.sh /usr/local/bin/bgpmon_write_metrics.sh
RUN chmod +x /usr/local/bin/bgpmon_write_metrics.sh

# Runtime config volume (compose mounts ./bird/config -> /etc/bird)
VOLUME ["/etc/bird"]

ENTRYPOINT ["/bin/bash", "/app/entrypoint.sh"]
