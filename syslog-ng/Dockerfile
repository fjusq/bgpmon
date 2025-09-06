FROM alpine:3.20

RUN apk add --no-cache syslog-ng

# Create log dir
RUN mkdir -p /var/log/syslog
VOLUME ["/var/log/syslog"]

COPY syslog-ng.conf /etc/syslog-ng/syslog-ng.conf

EXPOSE 8514/tcp 8514/udp

ENTRYPOINT ["syslog-ng", "-F", "-p", "/var/run/syslog-ng.pid", "-f", "/etc/syslog-ng/syslog-ng.conf"]
