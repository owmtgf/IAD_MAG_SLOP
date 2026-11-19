from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib import request


class LocalModel:
    """Минимальный клиент локального API /v1/chat/completions."""

    def __init__(self, base_url: str | None = None, model: str | None = None) -> None:
        self.base_url = (base_url or os.environ.get("MAS_LLM_URL", "http://127.0.0.1:8080/v1")).rstrip("/")
        self.model = model or os.environ.get("MAS_LLM_MODEL", "")
        self.binary = os.environ.get("MAS_LLAMA_COMPLETION")
        self.weights = os.environ.get("MAS_LLAMA_GGUF")
        if bool(self.binary) != bool(self.weights):
            raise ValueError("Задайте оба пути: MAS_LLAMA_COMPLETION и MAS_LLAMA_GGUF.")
        if self.binary and self.weights:
            self.binary = str(Path(self.binary).resolve(strict=True))
            self.weights = str(Path(self.weights).resolve(strict=True))
        try:
            self.timeout = float(os.environ.get("MAS_LLM_TIMEOUT", "60"))
        except ValueError:
            self.timeout = 0
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("MAS_LLM_TIMEOUT должен быть конечным числом секунд больше нуля.")

    def complete(
        self, *, agent: str, system: str, user: str, max_tokens: int = 200,
        choices: tuple[str, ...] = (),
    ) -> str:
        """Выполнить один вызов модели. agent нужен для журналирования роли."""
        if not self.model and not self.binary:
            raise ValueError("Укажите MAS_LLM_MODEL или параметр CLI --model.")
        if not agent.strip():
            raise ValueError("Имя агента должно быть непустым.")
        if any(len(x) != 1 or x not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" for x in choices):
            raise ValueError("Коды вариантов должны быть одиночными латинскими заглавными буквами.")
        user = user.replace("<|", "＜|")
        grammar = "root ::= " + " | ".join(json.dumps(choice) for choice in choices) if choices else ""
        print(json.dumps({"event": "llm_call", "agent": agent}, ensure_ascii=False), file=sys.stderr, flush=True)
        if self.binary:
            return self._complete_local(system, user, max_tokens, grammar)
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
                **({"grammar": grammar} if grammar else {}),
            },
            ensure_ascii=False,
        ).encode("utf-8")
        call = request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(call, timeout=self.timeout) as response:
            output = json.load(response)
        content = output["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"Пустой ответ модели для агента {agent}.")
        return content

    def _complete_local(self, system: str, user: str, max_tokens: int, grammar: str) -> str:
        prompt = (
            f"<|im_start|>system\n{system}<|im_end|>\n"
            f"<|im_start|>user\n{user}<|im_end|>\n<|im_start|>assistant\n"
        )
        with TemporaryDirectory(dir=Path.cwd(), prefix=".lr9-model-") as folder:
            file = Path(folder) / "prompt.txt"
            file.write_text(prompt, encoding="utf-8")
            command = [
                self.binary, "-m", self.weights, "-f", str(file), "-n", str(max_tokens),
                "--temp", "0", "--seed", "42", "--no-display-prompt", "--no-conversation",
                "--no-warmup", "-ngl", "0", "-t", "8", "-c", "2048",
            ]
            if grammar:
                command += ["--grammar", grammar]
            try:
                result = subprocess.run(
                    command, cwd=Path(self.binary).parent, stdin=subprocess.DEVNULL,
                    capture_output=True, timeout=self.timeout,
                )
            except subprocess.TimeoutExpired as error:
                raise TimeoutError(f"Qwen не ответил за {self.timeout:g} с.") from error
        if result.returncode:
            stderr = result.stderr.decode("utf-8", "replace")
            raise RuntimeError(f"llama-completion завершился с кодом {result.returncode}: {stderr[-1000:]}")
        output = result.stdout.decode("utf-8").strip().removesuffix("[end of text]").strip()
        if not output:
            raise ValueError("Модель вернула пустой ответ.")
        return output


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        answer = LocalModel().complete(
            agent="connection_check",
            system="Дайте короткий ответ на сообщение.",
            user="Ответьте одним словом: готово.",
            max_tokens=24,
        )
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError) as error:
        raise SystemExit(f"Проверка подключения к модели не прошла: {error}") from None
    print(f"Подключение к модели работает. Ответ: {answer}")


if __name__ == "__main__":
    main()

