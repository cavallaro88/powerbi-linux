# Build against glibc 2.39; Fedora 44 is the only supported execution target.
FROM ubuntu:24.04@sha256:534baea6a22c03a63003dbc8dbe78fe34bc0d7e595d9a9dc9834884ff530eb55
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential clang lld llvm flex bison meson ninja-build pkg-config git \
    ca-certificates curl xz-utils patch python3 mono-devel rpm glslang-tools spirv-tools \
    gcc-mingw-w64-x86-64-posix g++-mingw-w64-x86-64-posix \
    libfreetype-dev libunwind-dev libwayland-dev libegl-dev libxkbcommon-dev \
    libxkbregistry-dev libgnutls28-dev libsdl2-dev libvulkan-dev libfontconfig-dev \
    libpulse-dev libdbus-1-dev libudev-dev libasound2-dev libpcap-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
# Wine's i386 inline assembly triggers compiler crashes in the initial LLVM 18.
RUN apt-get update && apt-get install -y --no-install-recommends \
    clang-19=1:19.1.1-1ubuntu1~24.04.2 lld-19=1:19.1.1-1ubuntu1~24.04.2 llvm-19=1:19.1.1-1ubuntu1~24.04.2 file \
    && rm -rf /var/lib/apt/lists/*
RUN ln -sf /usr/bin/clang-19 /usr/local/bin/clang && \
    ln -sf /usr/bin/clang++-19 /usr/local/bin/clang++ && \
    ln -sf /usr/bin/lld-19 /usr/local/bin/lld && \
    ln -sf /usr/bin/ld.lld-19 /usr/local/bin/ld.lld
