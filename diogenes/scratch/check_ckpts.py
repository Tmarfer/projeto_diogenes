import sys
from pathlib import Path
import unicodedata

manifest_path = Path("/Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/workspace/cycles/MOD_010_A1_20260605T001056Z/manifest.md")
ckpt_dir = Path("/Users/tmarfer_mac/Documents/Projetos/projeto_diogenes/workspace/cycles/MOD_010_A1_20260605T001056Z/_runtime/watson_checkpoints")

def _watson_ckpt_path(ckpt_dir: Path, rel_path: str | Path) -> Path:
    safe = str(rel_path).replace("/", "__").replace("\\", "__").replace(":", "_")
    return ckpt_dir / f"{safe}.json"

print("Scanning manifest files...")
lines = manifest_path.read_text(encoding="utf-8").splitlines()
files = []
for line in lines:
    if "|" in line and "inputs/" in line:
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 5:
            # path is in parts[5] or we can search for inputs/
            for part in parts:
                if part.startswith("`inputs/"):
                    rel = part.replace("`inputs/", "").replace("`", "")
                    files.append(rel)

print(f"Found {len(files)} files in manifest.")

mismatches = 0
for f in files:
    expected_path = _watson_ckpt_path(ckpt_dir, f)
    exists = expected_path.exists()
    
    # Check normalization forms
    nfc_f = unicodedata.normalize('NFC', f)
    nfd_f = unicodedata.normalize('NFD', f)
    
    expected_nfc = _watson_ckpt_path(ckpt_dir, nfc_f)
    expected_nfd = _watson_ckpt_path(ckpt_dir, nfd_f)
    
    print(f"File: {f}")
    print(f"  NFD path exists: {expected_nfd.exists()} (path: {expected_nfd.name})")
    print(f"  NFC path exists: {expected_nfc.exists()} (path: {expected_nfc.name})")
    if not exists:
        mismatches += 1

print(f"Total mismatches: {mismatches}")
