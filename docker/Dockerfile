# ============================================================================
# GROMACS 2026.2 with CUDA GPU support
# ----------------------------------------------------------------------------

# ---------- build args -----------------------------------------------------
ARG CUDA_VERSION=12.8.0
ARG UBUNTU_VERSION=22.04
ARG GROMACS_VERSION=2026.2

# Target GPU architectures.
#   70 = V100, 75 = T4 / RTX 20xx, 80 = A100, 86 = A40 / RTX 30xx / L4,
#   89 = L40 / RTX 40xx / RTX 6000 Ada, 90 = H100 / GH200
ARG CUDA_ARCHITECTURES="70;75;80;86;89;90"

# ============================================================================
# Stage 1: builder
# ============================================================================
FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu${UBUNTU_VERSION} AS builder

ARG GROMACS_VERSION
ARG CUDA_ARCHITECTURES
ARG DEBIAN_FRONTEND=noninteractive

# --- toolchain & deps ------------------------------------------------------
# build-essential pulls GCC 11 on Ubuntu 22.04, which is supported by both
# CUDA 12.x and GROMACS 2026. cmake from apt is currently 3.22; GROMACS 2026
# requires >= 3.28
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates gnupg wget curl git \
        build-essential \
        libstdc++-12-dev \
        libfftw3-dev \
        libopenmpi-dev openmpi-bin \
        libhwloc-dev \
        libblas-dev liblapack-dev \
        python3 python3-pip \
        pkg-config \
        ninja-build \
    && wget -qO- https://apt.kitware.com/keys/kitware-archive-latest.asc \
         | gpg --dearmor - > /usr/share/keyrings/kitware-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/kitware-archive-keyring.gpg] https://apt.kitware.com/ubuntu/ jammy main" \
         > /etc/apt/sources.list.d/kitware.list \
    && apt-get update && apt-get install -y --no-install-recommends cmake \
    && rm -rf /var/lib/apt/lists/*

# --- fetch & extract GROMACS source ---------------------------------------
WORKDIR /opt
RUN wget -q https://ftp.gromacs.org/gromacs/gromacs-${GROMACS_VERSION}.tar.gz \
    && tar -xzf gromacs-${GROMACS_VERSION}.tar.gz \
    && rm gromacs-${GROMACS_VERSION}.tar.gz

# --- configure & build -----------------------------------------------------
# Key flags:
#   GMX_GPU=CUDA                      -> NVIDIA GPU acceleration via CUDA
#   GMX_MPI=ON                        -> OpenMPI for multi-node / multi-GPU
#   GMX_OPENMP=ON                     -> per-rank thread parallelism
#   GMX_BUILD_OWN_FFTW=OFF            -> use system libfftw3 (faster build)
#   GMX_SIMD=AUTO                     -> auto-detect host CPU SIMD at build
#   GMX_DOUBLE=OFF                    -> mixed precision (default, GPU-friendly)
#   CMAKE_CUDA_ARCHITECTURES          -> see ARG above
#   GMX_GPLUSGPLUS_PATH               -> point CUDA host compiler at g++-11
#   REGRESSIONTEST_DOWNLOAD=OFF       -> skip test-suite download in image
WORKDIR /opt/gromacs-${GROMACS_VERSION}/build
RUN cmake .. \
        -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_INSTALL_PREFIX=/usr/local/gromacs \
        -DGMX_GPU=CUDA \
        -DCMAKE_CUDA_ARCHITECTURES="${CUDA_ARCHITECTURES}" \
        -DGMX_MPI=ON \
        -DGMX_OPENMP=ON \
        -DGMX_FFT_LIBRARY=fftw3 \
        -DGMX_BUILD_OWN_FFTW=OFF \
        -DGMX_SIMD=AUTO \
        -DGMX_DOUBLE=OFF \
        -DGMX_HWLOC=ON \
        -DGMX_PREFER_STATIC_LIBS=OFF \
        -DGMX_GPLUSGPLUS_PATH=/usr/bin/g++ \
        -DREGRESSIONTEST_DOWNLOAD=OFF \
        -DBUILD_TESTING=OFF \
        -DGMXAPI=OFF \
    && ninja -j"$(nproc)" \
    && ninja install \
    && rm -rf /opt/gromacs-${GROMACS_VERSION}

# ============================================================================
# Stage 2: runtime
# ============================================================================
FROM nvidia/cuda:${CUDA_VERSION}-runtime-ubuntu${UBUNTU_VERSION}

ARG DEBIAN_FRONTEND=noninteractive

# Runtime libs only -- no compilers, no -dev packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libfftw3-3 \
        libopenmpi3 openmpi-bin openssh-client \
        libhwloc15 \
        libblas3 liblapack3 \
        libgomp1 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed GROMACS tree from the builder.
COPY --from=builder /usr/local/gromacs /usr/local/gromacs

# Make `gmx` / `gmx_mpi` visible without sourcing GMXRC on every invocation.
ENV PATH=/usr/local/gromacs/bin:$PATH \
    LD_LIBRARY_PATH=/usr/local/gromacs/lib:$LD_LIBRARY_PATH \
    MANPATH=/usr/local/gromacs/share/man:$MANPATH \
    GMXLIB=/usr/local/gromacs/share/gromacs/top \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility

RUN useradd -m -s /bin/bash gromacs
USER gromacs
WORKDIR /data

# Smoke-test that `gmx` resolves; replaced by real workload at runtime.
CMD ["gmx", "--version"]
