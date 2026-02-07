# 1 : Build stage
FROM rust:1.84-slim as builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
#KEEP
RUN cargo update -p home --precise 0.5.9
RUN cargo update -p base64ct --precise 1.6.0
RUN cargo build --release
RUN rm -f target/release/deps/public_server*
COPY . .
RUN cargo build --release

# 2 : Runtime stage
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/target/release/public_server /app/rust_api
EXPOSE 6668
CMD ["./rust_api"]