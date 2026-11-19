# speedR toolchain (node/speedr-node image): builds GNU R the way R builds by
# default, with one
# compiler for every version, and runs the timing pass. The compiler is GCC as
# upstream builds it (the official gcc image; Ubuntu's own GCC adds hardening
# by default). Everything else comes from the hosts' Ubuntu archive snapshot:
# the libraries R's configure finds, and Python for the drivers.
FROM gcc:16@sha256:5c2f83335c97e233c80d2bc754bd5c46b2d9c32f236a765a4ac40a59f216c064 AS gcc

FROM ubuntu:26.04@sha256:d66b366dac61b575bee2aef07e9c26e8070096fbe84a3d4d3eb0da069b5d76db

ARG SNAPSHOT=20261118T000000Z
# the snapshot is https-only and the base image has no CA certificates yet
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates \
 && sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu/?#https://snapshot.ubuntu.com/ubuntu/${SNAPSHOT}/#" \
        /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        binutils libc6-dev make perl \
        tcl8.6-dev tk8.6-dev bison groff-base libncurses-dev \
        libreadline-dev texinfo libbz2-dev liblzma-dev libpcre2-dev libcurl4-openssl-dev \
        xdg-utils zlib1g-dev libzstd1 libpng-dev libjpeg-dev libx11-dev libxt-dev x11proto-core-dev \
        libpango1.0-dev libcairo2-dev libtiff-dev libtirpc-dev \
        curl xz-utils bzip2 zip unzip locales python3 util-linux \
 && sed -i 's/^# *en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen && locale-gen \
 && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

# GCC 16 (gcc, g++, gfortran) in /usr/local, ahead of anything in /usr/bin
COPY --from=gcc /usr/local/ /usr/local/
RUN echo /usr/local/lib64 > /etc/ld.so.conf.d/gcc.conf && ldconfig

# PCRE1 for R < 4.0, which knows no PCRE2. Ubuntu no longer ships libpcre3, so
# build its last release with the same compiler and its own default flags,
# with the features Debian's pcre3 had. R >= 4.0 still picks PCRE2.
RUN curl -fsSL -o /tmp/pcre-8.45.tar.bz2 https://sourceforge.net/projects/pcre/files/pcre/8.45/pcre-8.45.tar.bz2/download \
 && echo "4dae6fdcd2bb0bb6c37b5f97c33c2be954da743985369cddac3546e3218bffb8  /tmp/pcre-8.45.tar.bz2" | sha256sum -c \
 && mkdir /build && tar -C /build -xjf /tmp/pcre-8.45.tar.bz2 && cd /build/pcre-8.45 \
 && ./configure --prefix=/usr/local --enable-utf8 --enable-unicode-properties \
        --enable-pcre16 --enable-pcre32 --enable-jit --disable-static \
 && make -j3 && make install && ldconfig \
 && cd / && rm -rf /build /tmp/pcre-8.45.tar.bz2
