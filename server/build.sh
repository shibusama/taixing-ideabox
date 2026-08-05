#!/bin/bash
set -e

echo "=== Installing Python dependencies ==="
pip install -r server/requirements.txt -q

echo "=== Installing ffmpeg ==="
apt-get update -qq && apt-get install -y -qq ffmpeg 2>/dev/null || echo "ffmpeg install skipped (not available)"

echo "=== Pre-downloading whisper model ==="
python3 -c "
from modelscope.hub.snapshot_download import snapshot_download
import os, shutil

model_name = 'Systran/faster-whisper-small'
hf_home = os.path.expanduser('~/.cache/huggingface')
model_cache_dir = os.path.join(hf_home, 'hub', 'models--systran--faster-whisper-small')

# Download from ModelScope
model_dir = snapshot_download(model_name, cache_dir=os.path.expanduser('~/.cache/modelscope'))
print(f'Model downloaded to: {model_dir}')

# Copy to huggingface cache
snap_dir = os.path.join(model_cache_dir, 'snapshots', 'modelscope_downloaded')
os.makedirs(snap_dir, exist_ok=True)
for f in os.listdir(model_dir):
    src = os.path.join(model_dir, f)
    dst = os.path.join(snap_dir, f)
    if os.path.isfile(src) and not os.path.exists(dst):
        shutil.copy2(src, dst)
        print(f'  Copied: {f}')

refs_dir = os.path.join(model_cache_dir, 'refs')
os.makedirs(refs_dir, exist_ok=True)
with open(os.path.join(refs_dir, 'main'), 'w') as f:
    f.write('modelscope_downloaded')

print('Model pre-download complete!')
"

echo "=== Build complete ==="