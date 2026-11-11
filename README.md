# Apptainer Workshop Containers

Container recipes for the Apptainer workshop. Each Dockerfile in [docker/](docker/) is built by GitHub Actions and published to the GitHub Container Registry (GHCR). From there you can pull it with Apptainer and run it on a workstation or an HPC cluster.

## Available images

| Application | Image | Contents |
|---|---|---|
| GROMACS | `ghcr.io/absrocks/apptainer-workshop/gromacs` | GROMACS 2026.2 with CUDA 12.8.0 and OpenMPI on Ubuntu 22.04 |

## Pulling an image with Apptainer

```bash
apptainer pull <name>.sif docker://ghcr.io/<github_user>/apptainer-workshop/<app>:<tag>
```

| Part | Meaning |
|---|---|
| `<name>.sif` | The image file to create. If you leave it out, Apptainer names the file `<app>_<tag>.sif`. |
| `docker://` | Tells Apptainer to download a Docker/OCI image and convert it to a SIF file. |
| `<app>` | The application name from the table above. |
| `<tag>` | The version to pull. `latest` is the most recent build. |

To pin one exact build, pull by digest instead of by tag:

```bash
apptainer pull <name>.sif docker://ghcr.io/<github_user>/apptainer-workshop/<app>@sha256:<digest>
```

The digests are listed on the package page, under **Packages** in the sidebar of this repository.


## Example: GROMACS

1. Pull the image. This creates `gromacs.sif` in the current directory.

   ```bash
   apptainer pull gromacs.sif docker://ghcr.io/absrocks/apptainer-workshop/gromacs:latest
   ```

2. Check that GROMACS runs.

   ```bash
   apptainer exec gromacs.sif gmx_mpi --version
   ```

   This image is built with MPI, so the executable is `gmx_mpi`, not `gmx`.

3. Run a simulation on a GPU. Start from the directory that holds your run input file, here `md.tpr`.

   ```bash
   cd /path/to/simulation
   apptainer exec --nv gromacs.sif gmx_mpi mdrun -deffnm md -ntomp 8
   ```

   - `--nv` makes the host's NVIDIA driver and GPUs available inside the container. It is required for GPU runs.
   - `-ntomp 8` sets the number of OpenMP threads. Match it to the CPU cores you have been allocated.
   - Apptainer mounts your home directory and the current directory by default. To reach data elsewhere, add `--bind /scratch/project`.

The image is compiled for these NVIDIA GPU generations: V100, T4, RTX 20xx/30xx/40xx, A100, A40, L4, L40, RTX 6000 Ada, H100 and GH200.

## Adding another image

1. Add the recipe as `docker/<app>_Dockerfile`.
2. Add `<app>` to the `matrix.app` list in [.github/workflows/build-and-push.yml](.github/workflows/build-and-push.yml).

On the next push, GitHub Actions builds the recipe and publishes it as `ghcr.io/absrocks/apptainer-workshop/<app>:latest`.
