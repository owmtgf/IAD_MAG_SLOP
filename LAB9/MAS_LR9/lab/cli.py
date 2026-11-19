from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .model import LocalModel
from .protocol import Request, Response
from .simulator import EquipmentSimulator
from .student import EquipmentDesk


def main() -> None:
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="ЛР9. Бюро выдачи оборудования, интерфейс JSON Lines")
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--model-url")
    parser.add_argument("--model")
    args = parser.parse_args()

    tools = EquipmentSimulator(args.state_dir, args.catalog)
    model = LocalModel(args.model_url, args.model)
    desk = EquipmentDesk(tools, model, args.state_dir)

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = Request.from_json(json.loads(line))
        except ValueError as error:
            response = Response("error", str(error))
        else:
            try:
                response = desk.handle(request)
            except NotImplementedError as error:
                response = Response("not_implemented", str(error))
        print(json.dumps(response.to_json(), ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()

