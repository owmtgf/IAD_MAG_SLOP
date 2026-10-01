# ЛР2: запуск и воспроизводимость

```bash
python -m unittest discover -s tests -v
python run.py --policy scripted --split dev --mode all --out results_scripted_dev
```

Использован Qwen3.5-4B через vLLM в приватной сети:

```bash
export MAS_LLM_BASE_URL=http://192.168.3.24:8000/v1
export MAS_LLM_MODEL=Qwen/Qwen3.5-4B
unset MAS_LLM_API_KEY

python run.py --policy llm --split dev --mode all --out results_llm_dev_qwen35_4b_v2
python run.py --policy llm --split test --mode all --repeats 2 --out results_llm_test_qwen35_4b
```

В `results_llm_test_qwen35_4b/` находятся CSV, run_config, JSON/JSONL трассы и разбивка по классам. Отчёт: `report.md`; учёт ИИ: `prompts.md`; негативные тесты: `tests/test_negative_checks.py`.
