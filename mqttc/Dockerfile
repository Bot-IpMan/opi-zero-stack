# mqttc/Dockerfile
FROM alpine:3.20
RUN apk add --no-cache mosquitto-clients ca-certificates
# лишаємо контейнер "живим", доки ти ним користуєшся
ENTRYPOINT ["/bin/sh","-lc","echo mqttc ready; tail -f /dev/null"]

