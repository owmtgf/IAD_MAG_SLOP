"""Execute a public project under Landlock or memory-only seccomp isolation.

The trusted mode is for offline author/reference validation, never live solving.
"""
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (15, 15))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024**2, 2 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))


def sandbox_command(project):
    return [sys.executable, "-I", str(ROOT / "worker.py"), "--sandbox", str(project)]


def execute(project, inputs, timeout=20, trusted_offline=False):
    project = Path(project).resolve()
    if trusted_offline:
        cmd = [sys.executable, "-I", str(ROOT / "worker.py"), str(project)]
    else:
        cmd = sandbox_command(project)
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        try:
            result = subprocess.run(cmd, input=json.dumps(inputs).encode(),
                                    stdout=output, stderr=errors, timeout=timeout,
                                    preexec_fn=limits,
                                    cwd=project, close_fds=True,
                                    env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"})
        except subprocess.TimeoutExpired:
            return {"error": "execution_timeout"}
        output.seek(0)
        raw = output.read(2 * 1024**2 + 1)
        errors.seek(0)
        stderr = errors.read(2000).decode(errors="replace")
    if result.returncode:
        return {"error": "execution_failed", "returncode": result.returncode, "detail": stderr}
    if len(raw) > 2 * 1024**2:
        return {"error": "output_limit"}
    try:
        values = json.loads(raw)
        if not isinstance(values, list) or len(values) != len(inputs):
            raise ValueError("Wrong number of results")
        return {"results": values}
    except (ValueError, TypeError):
        return {"error": "worker_output_invalid"}


def check(project, cases, timeout=20, trusted_offline=False):
    execution = execute(project, [c["input"] for c in cases], timeout, trusted_offline)
    if "error" in execution:
        return {"passed": False, "total": len(cases), "passed_count": 0, **execution}
    reports = []
    for case, result in zip(cases, execution["results"]):
        equal = result.get("ok") is True and json.dumps(result.get("value"), sort_keys=True, ensure_ascii=False) == json.dumps(case["expected"], sort_keys=True, ensure_ascii=False)
        reports.append({"id": case["id"], "passed": equal,
                        **({} if equal else {"input": case["input"], "expected": case["expected"], "actual": result})})
    count = sum(r["passed"] for r in reports)
    return {"passed": count == len(cases), "total": len(cases),
            "passed_count": count, "cases": reports}


def probe():
    with tempfile.TemporaryDirectory() as tmp:
        package = Path(tmp) / "app"
        package.mkdir()
        (package / "__init__.py").write_text("")
        # Exercise a lazy stdlib import after sandbox installation. A trivial
        # identity function misses inaccessible non-system runtime libraries.
        (package / "api.py").write_text(
            "from dataclasses import dataclass, asdict\n"
            "@dataclass\n"
            "class Probe:\n"
            "    probe: bool\n"
            "def solve(data):\n"
            "    return asdict(Probe(data['probe']))\n")
        report = execute(Path(tmp), [{"probe": True}], 10)
    if report != {"results": [{"ok": True, "value": {"probe": True}}]}:
        raise RuntimeError("Isolated executor unavailable: " + json.dumps(report, ensure_ascii=False))
