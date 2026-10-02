"""Run the whole studio on this machine, loopback only, with synthetic demos.

    pip install -r apps/api/requirements.txt -r apps/worker/requirements.txt -r requirements-test.txt
    python scripts/dev_studio.py            # then open http://127.0.0.1:8765

Starts a throwaway Postgres (+pgvector) and Redis from local binaries (or
uses E2E_DATABASE_URL / E2E_REDIS_URL), an S3-compatible store on loopback
standing in for internal MinIO, the real API (dev auth: GROUNDED_ENV=
development) and the real worker. Seeds synthetic briefings so the room has
something to show. Nothing binds beyond 127.0.0.1 and nothing leaves the box.
This is a developer convenience, not a deployment: use infra/compose.yaml.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "e2e"))

from stack import Stack, free_port  # noqa: E402


def workbook() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "KPI"
    ws.append(["Northwind Fulfilment — Week 32 Finance WBR"])
    ws.append(["Metric", "This week", "Last week", "Target"])
    rows = [
        ("Net revenue", 4820000, 4510000, 4600000, '"$"#,##0'),
        ("Gross margin", 0.412, 0.405, 0.42, "0.0%"),
        ("Orders shipped", 15200, 14100, 15000, "#,##0"),
        ("On-time delivery", 0.951, 0.962, 0.95, "0.0%"),
        ("Cost per order", 6.84, 7.02, 6.9, '"$"#,##0.00'),
    ]
    for label, now, prior, target, fmt in rows:
        ws.append([label, now, prior, target])
        for col in "BCD":
            ws[f"{col}{ws.max_row}"].number_format = fmt
    risks = wb.create_sheet("Risks")
    risks.append(["Risk", "Primary"])
    risks.append(["West-region carrier capacity is tight through week 34.", "yes"])
    asks = wb.create_sheet("Asks")
    asks.append(["Ask", "Primary"])
    asks.append(["Approve two weekend shifts at the Reno site.", "yes"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def package() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("week-32/finance-pack.xlsx", workbook())
        z.writestr(
            "week-32/ops-memo.md",
            "# Week 32 operations memo\n\nThe Reno site cleared its returns backlog on Tuesday.\n\n"
            "Risk: peak-season hiring is two weeks behind plan.\n\nApprove the overtime budget for week 33.",
        )
    return buf.getvalue()


def memo() -> bytes:
    return (
        "# Billing console launch\n\n## What ships\n\nThe new billing console replaces three legacy screens.\n\n"
        "Finance teams can export invoices in one step.\n\n## Rollout\n\nRollout starts with 12 pilot accounts.\n\n"
        "Approve the pilot list by Friday."
    ).encode()


def http(method: str, url: str, body: bytes | None = None, headers: dict | None = None) -> dict:
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=60) as response:
        return json.loads(response.read() or b"{}")


def multipart(field_file: tuple[str, bytes, str], kind: str) -> tuple[bytes, str]:
    boundary = "----groundeddev"
    name, data, mime = field_file
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"kind\"\r\n\r\n{kind}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\nContent-Type: {mime}\r\n\r\n".encode(),
        data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def seed(base: str) -> None:
    demos = [
        ("Week 32 finance review", "finance-wbr", ("week-32-pack.zip", package(), "application/zip")),
        ("Executive review — Q3", "executive-business-review", ("finance-pack.xlsx", workbook(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
        ("Billing console launch", "launch-announcement", ("billing-launch.md", memo(), "text/markdown")),
    ]
    for title, skill, upload in demos:
        created = http("POST", base + "/api/v1/briefings", json.dumps({"title": title, "skill_id": skill}).encode(), {"content-type": "application/json"})
        body, ctype = multipart(upload, "attachment")
        http("POST", f"{base}/api/v1/briefings/{created['id']}/assets", body, {"content-type": ctype})
        for job in ("ingest", "compile", "render", "index"):
            started = http("POST", f"{base}/api/v1/briefings/{created['id']}/jobs", json.dumps({"type": job}).encode(), {"content-type": "application/json"})
            for _ in range(240):
                state = http("GET", f"{base}/api/v1/jobs/{started['id']}")
                if state["state"] in {"succeeded", "failed"}:
                    break
                time.sleep(0.5)
            if state["state"] != "succeeded":
                print(f"  {title}: {job} failed — {state.get('error')}")
                break
        else:
            print(f"  seeded: {title}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-seed", action="store_true")
    args = parser.parse_args()

    stack = Stack().start()
    tmp = Path(tempfile.mkdtemp(prefix="grounded-dev-"))
    env = {
        **{k: v for k, v in os.environ.items() if not k.startswith(("GROUNDED_", "AWS_", "AUTH_", "OIDC_"))},
        "GROUNDED_DEPLOYMENT_MODE": "offline",
        "GROUNDED_ENV": "development",
        "DEV_BYPASS_AUTH": "true",
        "AUTH_MODE": "dev",
        "DEV_USER_EMAIL": "you@studio.local",
        "DATABASE_URL": stack.database_url,
        "REDIS_URL": stack.redis_url,
        "MINIO_ENDPOINT": stack.s3_url,
        "MINIO_BUCKET": "grounded-dev",
        "MINIO_ACCESS_KEY": "dev",
        "MINIO_SECRET_KEY": "dev",
        "GROUNDED_SKILLS_ROOT": str(ROOT / "skills"),
        "GROUNDED_TTS_PROVIDER": os.environ.get("GROUNDED_TTS_PROVIDER") or ("local" if shutil.which("piper") or os.environ.get("PIPER_BIN") else "none"),
        "GROUNDED_IMAGE_TEXT_PROVIDER": "local-ocr" if shutil.which("tesseract") else "none",
        "ARTIFACT_DIR": str(tmp / "jobs"),
        "HF_HUB_OFFLINE": "1",
        "PYTHONPATH": os.pathsep.join(str(ROOT / p) for p in ("apps/api", "apps/worker", "apps/engine")),
        "NO_PROXY": "127.0.0.1,localhost",
    }
    subprocess.run([sys.executable, "-m", "app.bootstrap"], env=env, check=True, cwd=ROOT / "apps" / "api")
    procs = [
        subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(args.port), "--log-level", "warning"], env=env, cwd=ROOT / "apps" / "api"),
        subprocess.Popen([sys.executable, "-m", "worker.main"], env=env, cwd=ROOT / "apps" / "worker"),
    ]
    base = f"http://127.0.0.1:{args.port}"

    def stop(*_args):
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
        stack.stop()
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    for _ in range(120):
        try:
            http("GET", base + "/health")
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.25)
    if not args.no_seed:
        print("Seeding synthetic briefings…")
        seed(base)
    print(f"\nGrounded Studio is running at {base}  (Ctrl+C to stop)\n")
    while all(proc.poll() is None for proc in procs):
        time.sleep(1)
    stop()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
