"""Один запуск проверяет все шесть сценариев и сохраняет трассы."""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description='Бюро бронирования — MCP, A2A, состояние и память')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--scenario', type=int, choices=range(1, 7), help='Запустить один из шести сценариев')
    modes.add_argument('--inspect', action='store_true', help='Показать Agent Card, инструменты и ресурсы MCP')
    modes.add_argument('--chat', action='store_true', help='Диалог через явно настроенный LLM endpoint (не оценивается)')
    args = parser.parse_args()
    try:
        from lab.scenarios import run_suite
        from lab.protocols import ProtocolLab
    except ImportError as error:
        print(f'Не установлены зависимости: {error}. Выполните: python -m pip install -r requirements.txt')
        return 2
    root = Path(__file__).resolve().parent
    output = root / 'runs' / datetime.now().strftime('%Y%m%d_%H%M%S_%f')

    async def run():
        if args.chat:
            from lab.llm import chat, InterpretationError
            try:
                await chat(root, output)
                return 0
            except InterpretationError as error:
                print(error)
                return 2
        if args.inspect:
            async with ProtocolLab(root, work_dir=output / 'inspect') as lab:
                print(json.dumps(await lab.inspect_protocols(), ensure_ascii=False, indent=2))
            print(f'Трасса: {output / "inspect" / "trace.jsonl"}')
            return 0
        report = await run_suite(root, output, selected=args.scenario)
        return 0 if report['passed'] == report['total'] else 1

    return asyncio.run(run())


if __name__ == '__main__':
    raise SystemExit(main())
