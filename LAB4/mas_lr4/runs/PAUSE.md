# Пауза итогового эксперимента по просьбе пользователя

Launcher PID 41399 и его дочерний core-процесс 41400 остановлены SIGTERM
как одна проверенная группа процессов. Отсутствие обоих процессов проверено.
Настройки, данные, инструкции и все три freeze сохранены; хеши совпадают.

До остановки завершены 184 эпизода core. Ещё один начатый эпизод,
T17_coordinator_b24000_r1, закрыт штатной командой close-interrupted:
статус interrupted, success=false, полный usage неизвестен. Трасса сохранена.
Он не будет повторён при продолжении. Всего записано 185/600 core;
осталось 415 core + 72 C + 24 M = 511 эпизодов.

После включения сервера с прежними моделью, окном 65536 и thinking=false,
из корня mas_lr4:

```bash
curl -sS --connect-timeout 5 http://192.168.3.42:8000/v1/models
MAS_LLM_BASE_URL=http://192.168.3.42:8000/v1 /home/owmtgf/anaconda3/bin/python -u scripts/run_final.py --resume
```

При желании оставить процесс в фоне в обычном пользовательском терминале:

```bash
nohup env MAS_LLM_BASE_URL=http://192.168.3.42:8000/v1 /home/owmtgf/anaconda3/bin/python -u scripts/run_final.py --resume >> runs/final_pipeline.log 2>&1 < /dev/null &
```

Выбрать один способ запуска. Не запускать две копии одновременно.
Нужен исходный Python 3.11.5 из /home/owmtgf/anaconda3/bin/python.
В окружении slop команда python указывает на Python 3.12.14; это вызывает
Resume manifest mismatch, поскольку версия интерпретатора входит в manifest.
Launcher пропустит сохранённые эпизоды и после core выполнит C и M.
Во время продолжения core-прогресс пишется в runs/final_core_resume.log.
Состояние: runs/final_pipeline_status.json. Новую freeze не создавать.
Если адрес или модель сервера изменились, сначала проверить совместимость
с сохранённым протоколом, не редактировать замороженные файлы наугад.
