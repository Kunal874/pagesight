"""Print torch version, CUDA availability, GPU name and free VRAM; exit 1 without a CUDA GPU."""

import torch

print(f"torch          : {torch.__version__}")
print(f"CUDA available : {torch.cuda.is_available()}")
if not torch.cuda.is_available():
    raise SystemExit(1)
free, total = torch.cuda.mem_get_info()
print(f"GPU            : {torch.cuda.get_device_name(0)}")
print(f"VRAM free      : {free / 2**30:.2f} of {total / 2**30:.2f} GiB")
