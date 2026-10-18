"""Receives inputs, never expected outputs; restricts access before app import."""
import contextlib
import copy
import importlib
import importlib.util
import io
import json
from pathlib import Path
import sys


class Discard(io.TextIOBase):
    def write(self, value):
        return len(value)


def main():
    arguments = sys.argv[1:]
    isolated = "--sandbox" in arguments
    if isolated:
        arguments.remove("--sandbox")
    if len(arguments) != 1:
        raise SystemExit("usage: worker.py [--sandbox] PUBLIC_PROJECT")
    project = Path(arguments[0]).resolve()
    inputs = json.load(sys.stdin)
    if isolated:
        # -I excludes the runner directory. Load only the trusted sandbox file
        # explicitly, without exposing the surrounding evaluator to imports.
        sandbox_path = Path(__file__).resolve().with_name("sandbox.py")
        spec = importlib.util.spec_from_file_location("_worker_sandbox", sandbox_path)
        sandbox = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sandbox)
        with contextlib.redirect_stdout(Discard()), contextlib.redirect_stderr(Discard()):
            sandbox.install(project, (Path(__file__).resolve(), sandbox_path))
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(project))
    outputs = []
    with contextlib.redirect_stdout(Discard()), contextlib.redirect_stderr(Discard()):
        try:
            solve = importlib.import_module("app.api").solve
        except Exception as exc:
            outputs = [{"ok": False, "error": type(exc).__name__, "detail": str(exc)[:1000]} for _ in inputs]
        else:
            for data in inputs:
                try:
                    argument = copy.deepcopy(data)
                    before = json.dumps(argument, sort_keys=True, ensure_ascii=False)
                    value = solve(argument)
                    if json.dumps(argument, sort_keys=True, ensure_ascii=False) != before:
                        raise ValueError("solve mutated input data")
                    # Serialize immediately: later calls must not mutate earlier results.
                    value = json.loads(json.dumps(value, allow_nan=False))
                    outputs.append({"ok": True, "value": value})
                except Exception as exc:
                    outputs.append({"ok": False, "error": type(exc).__name__, "detail": str(exc)[:1000]})
    print(json.dumps(outputs, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
