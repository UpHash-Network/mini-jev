"""Download only the pinned model files used by this release (about 8.1 GB)."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download

config=json.loads((Path(__file__).resolve().parent/'release_config.json').read_text())
print(snapshot_download(config['model'], revision=config['revision'],
    allow_patterns=['*.json','*.safetensors','*.txt','LICENSE'],max_workers=3))
