"""Работает до выполнения TODO. Показывает фиксированный процесс без оценивания."""
import json
from pathlib import Path
from core import Environment, ScriptedPolicy
from baseline import run_fixed
case = json.loads((Path(__file__).parent/"data/dev.json").read_text())[0]
print(json.dumps(run_fixed(ScriptedPolicy(), Environment(case)), ensure_ascii=False, indent=2))
