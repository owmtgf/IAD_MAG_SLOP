"""Готовый необязательный интерпретатор заявки. Не участвует в оценивании."""
import json
import os
from dataclasses import dataclass
from datetime import date
from typing import Literal
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class InterpretationError(ValueError):
    pass


class RequirementsPatch(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    date: str | None = None
    time: str | None = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    people: int | None = Field(default=None, ge=1, le=1000)
    projector: bool | None = None
    building: Literal['A', 'B'] | None = None

    @field_validator('date')
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
                raise ValueError('Используйте дату YYYY-MM-DD.')
        return value


class Remember(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    building: Literal['A', 'B']


class Interpretation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    patch: RequirementsPatch = Field(default_factory=RequirementsPatch)
    remember: Remember | None = None


@dataclass
class LLMConfig:
    base_url: str
    model: str
    api_key: str = ''

    @classmethod
    def from_environment(cls):
        base, model = os.environ.get('LLM_BASE_URL', '').strip(), os.environ.get('LLM_MODEL', '').strip()
        if not base or not model:
            raise InterpretationError('Для --chat задайте LLM_BASE_URL (с /v1) и LLM_MODEL. '
                                      'LLM_API_KEY нужен только если endpoint требует ключ.')
        parsed = urlparse(base)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise InterpretationError('LLM_BASE_URL должен быть полным HTTP(S) адресом.')
        return cls(base.rstrip('/'), model, os.environ.get('LLM_API_KEY', ''))


async def interpret(text, current, config):
    """Внешний запрос выполняется только при явном запуске --chat."""
    system = (
        'Извлеки из короткой реплики только ЯВНО указанные новые поля заявки на аудиторию. '
        'Верни один JSON-объект без markdown: {"patch": {...}, "remember": null}. '
        'patch может содержать date (YYYY-MM-DD), time (HH:MM), people (целое), '
        'projector (true/false), building ("A" или "B"). Неизвестные поля пропускай. '
        'Не выдумывай недостающую дату/время. Буквы корпусов возвращай латиницей. '
        'remember: {"building":"B"} допустим только при явной просьбе ЗАПОМНИТЬ '
        'предпочтение корпуса, иначе null. Не возвращай confirm, ID, состояние или бронь. '
        'Для подтверждения пользователь использует отдельную команду /confirm. '
        'Текущие требования, только для контекста: ' + json.dumps(current, ensure_ascii=False)
    )
    headers = {'Authorization': 'Bearer ' + config.api_key} if config.api_key else {}
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            response = await client.post(config.base_url + '/chat/completions', headers=headers,
                json={'model': config.model, 'temperature': 0, 'max_tokens': 256,
                      'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': text}]})
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
        parsed = Interpretation.model_validate_json(content)
        payload = parsed.model_dump(exclude_none=True)
        if not payload['patch'] and not payload.get('remember'):
            raise InterpretationError('Модель не извлекла данных. Укажите дату, время или другое поле явно.')
        if parsed.remember and 'запомни' not in text.lower():
            raise InterpretationError('Модель предложила изменить память без явной просьбы «запомни».')
        return payload
    except InterpretationError:
        raise
    except httpx.HTTPError as error:
        raise InterpretationError('Не удалось обратиться к endpoint модели. Проверьте адрес, модель и ключ; '
                                  f'тип ошибки: {type(error).__name__}. Заявка не отправлена.') from error
    except (ValidationError, ValueError, KeyError, IndexError, TypeError) as error:
        raise InterpretationError('Ответ модели не соответствует схеме заявки. '
                                  'Заявка не отправлена; уточните реплику и повторите.') from error


async def chat(root, output):
    from .protocols import ProtocolLab
    import asyncio

    config = LLMConfig.from_environment()  # Проверяем настройки до запуска сервисов.
    print('Режим с LLM. Реплика → проверенные поля → тот же A2A/MCP контур.')
    print('Команды: /confirm — подтвердить предложенный вариант; /new — новая задача; /exit — выход.')
    print('Пример: «2026-11-01 в 10:00, 20 человек, проектор, корпус A».')
    current = None
    async with ProtocolLab(root, work_dir=output / 'chat') as lab:
        while True:
            try:
                text = (await asyncio.to_thread(input, '> ')).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text == '/exit':
                break
            if text == '/new':
                current = None
                print('Начата новая заявка; долговременный профиль сохранен.')
                continue
            if not text:
                continue
            if current and current['phase'] == 'completed':
                print('Задача уже завершена. Для другой брони введите /new.')
                continue
            try:
                if text == '/confirm':
                    if not current or current['phase'] != 'waiting_confirmation':
                        print('Сначала получите предложение аудитории.')
                        continue
                    payload = {'confirm': True}
                else:
                    payload = await interpret(text, current['requirements'] if current else {}, config)
                    print('Распознано: ' + json.dumps(payload, ensure_ascii=False))
                current = await lab.send('demo-user', payload,
                    task_id=current['task_id'] if current else None,
                    context_id=current['context_id'] if current else None)
                print(current['text'])
                print(f"Task: {current['task_id']} | {current['a2a_state']}")
            except InterpretationError as error:
                print(error)
    print(f'Трасса: {output / "chat" / "trace.jsonl"}')
