"""Download every model the app can use, so later runs work offline."""
from . import config, engine

for name in sorted(set(config.MODELS.values())):
    print(f"Downloading {name} ...", flush=True)
    engine._load(name)
    print(f"  ready: {name}", flush=True)
print("All models downloaded.")
