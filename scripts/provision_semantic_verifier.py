"""Provision pinned full precision NLI weights outside the scientific corpus."""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from nasa_fire_ai.services.semantic_support import MODEL_REPOSITORY, MODEL_REVISION


def main():
    from huggingface_hub import hf_hub_download

    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if "data/raw" in args.output.resolve().as_posix():
        parser.error("Model weights do not belong in raw scientific data")
    args.output.mkdir(parents=True, exist_ok=True)
    receipts = []
    for remote in ["config.json", "tokenizer.json", "onnx/model.onnx"]:
        path = Path(hf_hub_download(MODEL_REPOSITORY, remote, revision=MODEL_REVISION))
        target = args.output / path.name
        shutil.copyfile(path, target)
        with target.open("rb") as stream:
            checksum = hashlib.file_digest(stream, "sha256").hexdigest()
        receipts.append({"file": target.name, "sha256": checksum, "bytes": target.stat().st_size})
    (args.output / "manifest.json").write_text(
        json.dumps(
            {"repository": MODEL_REPOSITORY, "revision": MODEL_REVISION, "files": receipts},
            indent=2,
        )
        + "\n"
    )
    print(f"Verifier provisioned in {args.output}; set NASA_NLI_DIRECTORY to this directory.")


if __name__ == "__main__":
    main()
