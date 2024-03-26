from --platform=linux/amd64 ubuntu:22.04

env DEBIAN_FRONTEND=noninteractive

run apt-get update && \
    apt-get install \
        -y \
        --no-install-recommends \
        wget ca-certificates

# install nodeos
workdir /root
run wget https://github.com/telosnetwork/leap/releases/download/v4.0.4-1.0.2-rc1/leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb && \
    apt-get install -y -f ./leap_4.0.4-1-0-2-ubuntu22.04_amd64.deb

workdir /
