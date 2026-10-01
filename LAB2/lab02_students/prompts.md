# Использование ИИ

## Рабочий агент

Финальная версия промпта: `agent_prompt.txt`. Модель: Qwen3.5-4B через локальный vLLM и OpenAI-совместимый `/v1/chat/completions`. Параметры: temperature=0.2, max_tokens=256, max_steps=12. На сервере отключён thinking-режим, поэтому ответом является один JSON.

На dev сначала было 8/10 успехов agent: в stale-сценариях модель передавала `resource_id` в `validate_assignment`. В промпт добавлены правила перечитывания ресурсов после `assignment_blocked` и вызова `validate_assignment` только с `args={}`. После этого agent получил 10/10 на dev. Test для настройки не использовался; итог — 39/40.

## Помощь при подготовке работы

Использован Codex/GPT-5, реализация цикла и evaluator, разбор трасс, настройка vLLM endpoint, негативные тесты и отчёт. Код проверен unit-тестами, scripted, LLM dev и LLM test.
