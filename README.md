# Installing Libraries 
.

### Step 1 — Python environment

```bash
cd RoboDel
conda create -y -n robodel python=3.10
conda activate robodel
pip install -r requirements.txt

# vulkaninfo is a binary, not a pip package; xorg-libxext is needed in step 3
conda install -y -c conda-forge vulkan-tools xorg-libxext
```

### Step 2 — Unity build

The first run downloads AI2-THOR's Unity build (~800 MB zipped, 1.1 GB unpacked)
into `~/.ai2thor`. Fetch it up front so the first render can't time out:

```bash
python -c "
from ai2thor.controller import Controller
from ai2thor.platform import CloudRendering
Controller(platform=CloudRendering, download_only=True)"
```

It lands in `~/.ai2thor/releases/thor-CloudRendering-<commit>/`, where `<commit>`
is the build pinned by the installed `ai2thor` (5.0.0 →
`f0825767cd50d69f666c7f282e54abfe58f1e917`). The path is hardcoded, so to keep
the build off your home partition, symlink `~/.ai2thor` elsewhere *before*
downloading.

Rendering uses AI2-THOR's `CloudRendering` platform — headless Vulkan, no X
server required.

### Step 3 — Graphics libraries, if the container lacks them

Run `vulkaninfo --summary` first. If it lists your NVIDIA GPU under `Devices:`,
skip to step 4. If it lists only `llvmpipe` (Mesa's CPU rasterizer) or nothing,
read on.

A GPU container image often ships CUDA and nothing else. The NVIDIA driver
libraries get mounted in by the container runtime, but the userspace they depend
on is absent, and the failure surfaces far from its cause:

```
RuntimeError: Could not find a Vulkan device corresponding to the CUDA device
with UUID <uuid>.
```

That is AI2-THOR reporting that `vulkaninfo` showed it no NVIDIA device. CUDA
works throughout — `nvidia-smi` and `cuInit` are fine — because only the
*graphics* path is broken. Two libraries are usually missing, and neither needs
root to supply:

- **`libXext.so.6`**, a hard `DT_NEEDED` of `libGLX_nvidia.so.0`. Without it the
  loader cannot open the ICD at all and logs `Failed to CreateInstance in ICD`.
- **libglvnd** (`libGL.so.1`, `libEGL.so.1`, `libGLdispatch.so.0`,
  `libGLX.so.0`, `libOpenGL.so.0`). `libGLX_nvidia.so.0` is a GLVND *vendor*
  library and refuses to initialize without the dispatch layer even when it is
  being used purely as a Vulkan ICD — `vk_icdNegotiateLoaderICDInterfaceVersion`
  returns `-3` (`VK_ERROR_INITIALIZATION_FAILED`) and every entry point comes
  back NULL. This one is easy to misdiagnose: no file access fails, and the
  driver never touches `/dev/nvidia*`, so `strace` shows nothing obviously wrong.

Stage both into one directory and put it on `LD_LIBRARY_PATH`:

```bash
conda create -y -p /tmp/glvnd -c conda-forge \
    libglvnd-cos7-x86_64 libglvnd-glx-cos7-x86_64 \
    libglvnd-egl-cos7-x86_64 libglvnd-opengl-cos7-x86_64
mkdir -p ~/.local/vulkanfix/lib
cp -P /tmp/glvnd/x86_64-conda-linux-gnu/sysroot/usr/lib64/lib{GL,EGL,GLX,GLdispatch,OpenGL}.so* \
      ~/.local/vulkanfix/lib/
cp -P $CONDA_PREFIX/lib/libXext.so.6* ~/.local/vulkanfix/lib/   # conda install -c conda-forge xorg-libxext

export LD_LIBRARY_PATH=~/.local/vulkanfix/lib
vulkaninfo --summary        # should now list your NVIDIA device
```

Make it automatic so every shell inherits it, rather than exporting by hand:

```bash
mkdir -p $CONDA_PREFIX/etc/conda/{activate,deactivate}.d

cat > $CONDA_PREFIX/etc/conda/activate.d/thor3d_vulkan.sh <<'EOF'
export _THOR3D_OLD_LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
export LD_LIBRARY_PATH="$HOME/.local/vulkanfix/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
EOF

cat > $CONDA_PREFIX/etc/conda/deactivate.d/thor3d_vulkan.sh <<'EOF'
if [ -n "${_THOR3D_OLD_LD_LIBRARY_PATH+x}" ]; then
    if [ -z "$_THOR3D_OLD_LD_LIBRARY_PATH" ]; then unset LD_LIBRARY_PATH
    else export LD_LIBRARY_PATH="$_THOR3D_OLD_LD_LIBRARY_PATH"; fi
    unset _THOR3D_OLD_LD_LIBRARY_PATH
fi
EOF
```

`activate.d` runs only at activation, so re-activate before testing:
`conda deactivate && conda activate thor3d`.

### Step 4 — GPU index

Find which CUDA index has a working Vulkan device, because it is often not 0:

```bash
nvidia-smi -L                                             # CUDA index -> GPU-<uuid>
vulkaninfo --summary | grep -E "^GPU[0-9]|deviceUUID"     # Vulkan index -> deviceUUID
```

Match the UUIDs. The CUDA index whose UUID appears in the `vulkaninfo` output is
the one to pass as `--gpu`. A GPU listed by `nvidia-smi` but absent from
`vulkaninfo` cannot render — a faulty card, or one the container exposes for
compute only.

If *every* GPU matches, AI2-THOR builds the mapping itself and there is nothing
to do. If any GPU is unmatched it raises regardless of which index you asked for,
because it insists on mapping all of them:

```
RuntimeError: Could not find a Vulkan device corresponding to the CUDA device
with UUID <uuid>.
```

Write the map by hand to bypass that. It is the only thing AI2-THOR's
`-force-device-index` flag is derived from:

```bash
echo '{"1": 0}' > ~/.ai2thor/cuda-vulkan-mapping.json   # CUDA 1 -> Vulkan 0
```

Then pass `--gpu 1` — the CUDA index, the key on the left — to every script and
to the web app. An index missing from the map fails immediately with
`KeyError: <index>`, which is the good case; the bad case is a map pointing at a
CPU device, which renders silently and slowly (see the CPU section below).

This file is a cache AI2-THOR never revalidates, so rewrite it whenever the set
of visible GPUs changes.
.