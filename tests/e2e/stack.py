"""Start a throwaway private stack on loopback: Postgres+pgvector, Redis, S3.

Used by the end-to-end tests. Everything binds to 127.0.0.1; nothing is
reachable from outside the test host. In CI the workflow provides Postgres
and Redis as service containers (E2E_DATABASE_URL / E2E_REDIS_URL); locally
this module starts its own from the installed binaries. The S3 API is the
moto server, standing in for internal MinIO.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import tempfile
import time
import uuid
from contextlib import closing
from pathlib import Path


def free_port() -> int:
    with closing(socket.socket()) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _pg_bin(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for base in sorted(Path("/usr/lib/postgresql").glob("*/bin"), reverse=True):
        if (base / name).exists():
            return str(base / name)
    return None


class Stack:
    def __init__(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="grounded-e2e-"))
        self.procs: list[subprocess.Popen] = []
        self.pg_dir: Path | None = None
        self.database_url = ""
        self.redis_url = ""
        self.s3_url = ""
        self._moto = None

    # ---------------------------------------------------------------- start
    def start(self) -> "Stack":
        self._postgres()
        self._redis()
        self._s3()
        return self

    def _as_postgres(self, args: list[str]) -> list[str]:
        if os.geteuid() == 0:
            return ["runuser", "-u", "postgres", "--", *args]
        return args

    def _postgres(self) -> None:
        external = os.environ.get("E2E_DATABASE_URL")
        name = "grounded_e2e_" + uuid.uuid4().hex[:8]
        if external:
            from sqlalchemy import create_engine, text

            admin = create_engine(external, isolation_level="AUTOCOMMIT")
            with admin.connect() as conn:
                conn.execute(text(f"CREATE DATABASE {name}"))
            admin.dispose()
            self.database_url = external.rsplit("/", 1)[0] + "/" + name
            return
        initdb, pg_ctl = _pg_bin("initdb"), _pg_bin("pg_ctl")
        if not initdb or not pg_ctl:
            raise RuntimeError("postgres binaries not found; set E2E_DATABASE_URL")
        self.pg_dir = self.tmp / "pg"
        self.pg_dir.mkdir()
        if os.geteuid() == 0:
            shutil.chown(self.tmp, "postgres")
            shutil.chown(self.pg_dir, "postgres")
        port = free_port()
        subprocess.run(self._as_postgres([initdb, "-D", str(self.pg_dir), "-U", "grounded", "--auth=trust", "-E", "UTF8"]),
                       check=True, capture_output=True)
        subprocess.run(
            self._as_postgres([pg_ctl, "-D", str(self.pg_dir), "-o", f"-p {port} -h 127.0.0.1 -k {self.pg_dir}", "-l", str(self.pg_dir / "log"), "-w", "start"]),
            check=True, capture_output=True,
        )
        base = f"postgresql+psycopg://grounded@127.0.0.1:{port}"
        from sqlalchemy import create_engine, text

        admin = create_engine(base + "/postgres", isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            conn.execute(text(f"CREATE DATABASE {name}"))
        admin.dispose()
        self.database_url = f"{base}/{name}"

    def _redis(self) -> None:
        external = os.environ.get("E2E_REDIS_URL")
        if external:
            self.redis_url = external
            return
        binary = shutil.which("redis-server")
        if not binary:
            raise RuntimeError("redis-server not found; set E2E_REDIS_URL")
        port = free_port()
        proc = subprocess.Popen([binary, "--port", str(port), "--bind", "127.0.0.1", "--save", "", "--appendonly", "no"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.procs.append(proc)
        self.redis_url = f"redis://127.0.0.1:{port}/0"
        self._wait(port)

    def _s3(self) -> None:
        from moto.server import ThreadedMotoServer

        port = free_port()
        self._moto = ThreadedMotoServer(ip_address="127.0.0.1", port=port, verbose=False)
        self._moto.start()
        self.s3_url = f"http://127.0.0.1:{port}"
        self._wait(port)

    @staticmethod
    def _wait(port: int, timeout: float = 15.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError(f"port {port} did not open")

    # ---------------------------------------------------------------- stop
    def stop(self) -> None:
        if self._moto is not None:
            self._moto.stop()
        for proc in self.procs:
            proc.terminate()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if self.pg_dir is not None:
            pg_ctl = _pg_bin("pg_ctl")
            subprocess.run(self._as_postgres([pg_ctl, "-D", str(self.pg_dir), "-m", "immediate", "stop"]), capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)
