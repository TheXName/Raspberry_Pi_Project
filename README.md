# FurnacePi

Python-проект для переноса управления печью с внешнего ПК/MATLAB на Raspberry Pi.

## Что реализовано

- Чтение Agilent 34972A через PyVISA/PyVISA-py, с mock-режимом для разработки без прибора.
- Чтение TEGAM 3550 через RS-232/pySerial, с терпимым парсером числовых ответов.
- Управление печью через GPIO и SSR в режиме time-proportioning, безопасно OFF на старте и при завершении.
- Температурная программа ramp/soak из `config.example.toml`.
- Программные interlocks: перегрев, таймаут датчика, слишком длинная задержка control loop.
- Логирование в `Results/Data-YYYY-MM-DD_HHMMSS.dt` и sidecar JSON с конфигурацией запуска.
- `systemd` unit и заготовка `udev`-правил для Raspberry Pi.

## Быстрый запуск на ПК без железа

```bash
python -m pip install -e .
python main.py --config config.example.toml --dry-run-seconds 5
```

После запуска появится папка `Results/` с `.dt`-файлом.

## Raspberry Pi deployment

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libusb-1.0-0
sudo mkdir -p /opt/furnacepi /etc/furnacepi /opt/furnacepi/Results
python3 -m venv /opt/furnacepi/.venv
/opt/furnacepi/.venv/bin/pip install pyvisa pyvisa-py pyserial pyusb gpiozero
```

Скопируйте проект в `/opt/furnacepi`, а рабочий конфиг в `/etc/furnacepi/config.toml`.

Для реального запуска поменяйте в конфиге:

- `[agilent].mock = false`
- `[tegam].mock = false`
- `[heater].mock = false`
- `[agilent].resource` на VISA-адрес 34972A, например `TCPIP0::192.168.1.50::inst0::INSTR`
- `[tegam].port` на стабильный путь адаптера, например `/dev/tegam3550`
- `[tegam].measurement_command` и `terminator` на точные значения из старого MATLAB-кода/мануала TEGAM

## Проверки перед печью

```bash
/opt/furnacepi/.venv/bin/python -m serial.tools.list_ports -v
/opt/furnacepi/.venv/bin/pyvisa-info
/opt/furnacepi/.venv/bin/furnacepi-preflight --config /etc/furnacepi/config.toml --list-ports
```

Сначала проверьте Agilent `*IDN?`, затем TEGAM command/response, затем SSR на лампе или dummy load. Только после этого подключайте печь через аппаратный interlock/термостат.

## Важное по безопасности

Программа всегда выключает нагреватель при exception, SIGTERM/SIGINT и штатном завершении, но software safety не заменяет аппаратную защиту. Силовая цепь печи должна иметь SSR/контактор, предохранитель, заземление и независимый overtemperature cut-off.
