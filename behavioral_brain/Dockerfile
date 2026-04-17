# ---------- build stage ----------
FROM golang:1.21-alpine AS builder

WORKDIR /src
COPY go.mod .
RUN go mod download || true
COPY . .
RUN CGO_ENABLED=0 GOARCH=arm64 GOOS=linux \
    go build -ldflags="-s -w" -o /sentry ./cmd/sentry/

# ---------- runtime stage ----------
FROM gcr.io/distroless/static:nonroot

COPY --from=builder /sentry /sentry

ENV LISTEN_ADDR=:8080

EXPOSE 8080
ENTRYPOINT ["/sentry"]
