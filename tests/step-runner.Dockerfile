FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends bash jq git curl ca-certificates gettext-base python3 python3-yaml findutils gawk sed grep coreutils >/dev/null && rm -rf /var/lib/apt/lists/*
