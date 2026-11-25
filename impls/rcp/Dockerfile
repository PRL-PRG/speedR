# speedR's image for rcp (node/speedr-node image): the toolchain image GNU R
# builds in, plus libbfd, for the tool that extracts rcp's stencils from the
# compiled object file. A layer of its own: the toolchain image, and with it
# every GNU R build id, stays as it is.
FROM speedr-toolchain
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends binutils-dev \
 && rm -rf /var/lib/apt/lists/*
