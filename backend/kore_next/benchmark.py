"""Batch inference for SWE-bench Verified and FeatureBench fast."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def load_rows(benchmark: str, ids: set[str], limit: int | None) -> list[dict]:
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Install the runner dependency: pip install datasets") from exc
    name, split, revision = (
        ("princeton-nlp/SWE-bench_Verified", "test", None)
        if benchmark == "swebench" else ("LiberCoders/FeatureBench", "fast", "v1.1")
    )
    dataset = load_dataset(name, split=split, revision=revision)
    rows = [dict(row) for row in dataset if not ids or row["instance_id"] in ids]
    if ids - {row["instance_id"] for row in rows}:
        raise ValueError(f"Unknown task IDs: {sorted(ids - {row['instance_id'] for row in rows})}")
    return rows[:limit] if limit else rows


def docker_command(benchmark: str, row: dict, image: str) -> list[str]:
    env_names = ("KORENEXT_PROVIDER", "KORENEXT_MODEL", "KORENEXT_API_KEY", "KORENEXT_BASE_URL",
                 "KORENEXT_MAX_STEPS", "KORENEXT_RUN_WARNING_MODEL_CALLS", "KORENEXT_RUN_FINALIZATION_MODEL_CALLS",
                 "KORENEXT_RUN_HARD_MODEL_CALLS", "KORENEXT_RUN_WARNING_TOKENS",
                 "KORENEXT_RUN_FINALIZATION_TOKENS", "KORENEXT_RUN_HARD_TOKENS")
    command = ["docker", "run", "--rm", "-i", "--platform", "linux/amd64", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges", "--pids-limit", "512"]
    for name in env_names:
        if name in os.environ:
            command.extend(["-e", name])
    command.extend(["-e", "KORENEXT_BENCHMARK_CONTAINER=true", "-e", "KORENEXT_DATA_DIR=/tmp/yunagent-data",
                    "-e", f"KORENEXT_MAX_STEPS={os.environ.get('KORENEXT_MAX_STEPS', '50')}",
                    "-e", f"KORENEXT_RUN_WARNING_MODEL_CALLS={os.environ.get('KORENEXT_RUN_WARNING_MODEL_CALLS', '48')}",
                    "-e", f"KORENEXT_RUN_FINALIZATION_MODEL_CALLS={os.environ.get('KORENEXT_RUN_FINALIZATION_MODEL_CALLS', '56')}",
                    "-e", f"KORENEXT_RUN_HARD_MODEL_CALLS={os.environ.get('KORENEXT_RUN_HARD_MODEL_CALLS', '64')}"])
    if benchmark == "swebench":
        command.extend(["-e", "KORENEXT_WORKSPACE_DIR=/tmp/yunagent-workspace", image,
                        "python", "-m", "kore_next.benchmark_worker"])
    else:
        backend = Path(__file__).resolve().parents[1]
        command.extend(["--mount", f"type=bind,src={backend},dst=/opt/yunagent,readonly",
                        "-e", "KORENEXT_WORKSPACE_DIR=/testbed", "-e", "PYTHONPATH=/opt/yunagent:/tmp/yunagent-deps",
                        "--entrypoint", "bash", str(row["image_name"]), "-lc",
                        "source ~/.bashrc; conda activate testbed 2>/dev/null || true; "
                        "python -m pip install --quiet --target /tmp/yunagent-deps -r /opt/yunagent/requirements.txt "
                        "&& python -m kore_next.benchmark_worker"])
    return command


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", choices=("swebench", "featurebench"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--image", default="yunagent:benchmark", help="YunAgent image for SWE-bench inference")
    parser.add_argument("--instance-id", action="append", default=[])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true", help="Append missing tasks to an existing predictions file")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args()
    if not os.environ.get("KORENEXT_API_KEY"):
        parser.error("KORENEXT_API_KEY is required")
    if not shutil.which("docker"):
        parser.error("Docker CLI is required on the runner host")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    rows = load_rows(args.benchmark, set(args.instance_id), args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    completed = set()
    if args.resume and args.output.exists():
        with args.output.open(encoding="utf-8") as existing:
            completed = {json.loads(line)["instance_id"] for line in existing if line.strip()}
    with args.output.open("a" if args.resume else "w", encoding="utf-8") as output:
        for index, row in enumerate(rows, 1):
            task_id = row["instance_id"]
            if task_id in completed:
                continue
            print(f"[{index}/{len(rows)}] {task_id}", file=sys.stderr)
            command = docker_command(args.benchmark, row, args.image)
            try:
                run = subprocess.run(command, input=json.dumps({"benchmark": args.benchmark, "row": row}),
                                     text=True, capture_output=True, timeout=args.timeout + 300)
                marker = next((line.removeprefix("YUNAGENT_BENCH_RESULT=") for line in reversed(run.stdout.splitlines())
                               if line.startswith("YUNAGENT_BENCH_RESULT=")), None)
                if run.returncode or marker is None:
                    raise RuntimeError((run.stderr or run.stdout)[-3000:])
                prediction = json.loads(marker)
            except (subprocess.TimeoutExpired, RuntimeError) as exc:
                print(f"{task_id}: {exc}", file=sys.stderr)
                prediction = {"instance_id": task_id, "model_patch": ""}
                if args.benchmark == "swebench":
                    prediction["model_name_or_path"] = "YunAgent"
                else:
                    prediction.update(agent="yunagent", model=os.environ.get("KORENEXT_MODEL", ""), n_attempt=1,
                                      task_metadata={}, success=False, error=str(exc), agent_exit_status="failed")
            output.write(json.dumps(prediction, ensure_ascii=False) + "\n")
            output.flush()


if __name__ == "__main__":
    main()
