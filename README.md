# FurnacePi

Python-проект для переноса управления печью с внешнего ПК/MATLAB на Raspberry Pi.

По умолчанию `python main.py` теперь запускает `config.real.toml`. Это реальный конфиг для Raspberry Pi. Для безопасной проверки без железа запускайте явно:

```bash
python main.py --config config.example.toml --dry-run-seconds 10
```

## Что реализовано

- Agilent 34972A через PyVISA/PyVISA-py.
- TEGAM 3550 через RS-232/pySerial.
- GPIO-управление SSR/relay driver в режиме медленного time-proportioning.
- Температурная программа ramp/soak.
- Safety interlocks: перегрев, таймаут датчика, слишком длинная задержка control loop.
- Запись логов `Results/Data-YYYY-MM-DD_HHMMSS.dt`.
- `systemd` unit и заготовка `udev`-правил.

## Важные конфиги

- `config.example.toml` - безопасная симуляция, все `mock = true`.
- `config.real.toml` - реальный запуск, все основные `mock = false`.

В `config.real.toml` есть словацкие комментарии, где вводить:

- IP/VISA адрес Agilent;
- serial port TEGAM;
- GPIO pin SSR/relay driver;
- температурные лимиты;
- температурную программу.

## Что сделать после переноса на Raspberry Pi

1. Установить системные пакеты:

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip libusb-1.0-0
```

2. Скопировать проект, например в `/opt/furnacepi`.

3. Создать окружение и установить зависимости:

```bash
cd /opt/furnacepi
python3 -m venv .venv
.venv/bin/pip install -e .
```

4. Проверить serial adapter TEGAM:

```bash
.venv/bin/python -m serial.tools.list_ports -v
```

Если видите `/dev/ttyUSB0`, `/dev/ttyUSB1` и т.п., запишите правильный порт в `config.real.toml`. Лучше позже сделать стабильный alias `/dev/tegam3550` через `udev/99-furnacepi.rules`.

5. Проверить Agilent:

```bash
.venv/bin/pyvisa-info
.venv/bin/furnacepi-preflight --config config.real.toml --skip-agilent-idn
```

Когда IP Agilent точно настроен, запустите уже без `--skip-agilent-idn`:

```bash
.venv/bin/furnacepi-preflight --config config.real.toml --list-ports
```

6. Первый запуск делать без печи:

```bash
python main.py --config config.example.toml --dry-run-seconds 10
```

7. Потом проверить реальные приборы, но оставить нагрев отключенным физически или через `heater.mock = true`.

8. Проверить SSR/relay driver на лампе или dummy load, не на печи.

9. Только после этого подключать печь через аппаратный interlock/термостат и запускать низкотемпературный короткий профиль.

## Про TEGAM команды

Точные команды из старого MATLAB-проекта пока неизвестны. В `config.real.toml` поставлена наиболее вероятная стартовая последовательность для TEGAM 3550 RS-232:

```toml
startup_commands = ["E3", "REN", "O1"]
measurement_command = "T0"
```

По мануалу 3550: `REN` включает вывод измерительных данных, `O1` выбирает RS-232 output, `E3` соответствует запуску измерения командой, а `T0` является trigger command. Но это всё равно надо проверить на вашем приборе. Если старый MATLAB-код посылал другие строки, замените их в `config.real.toml`.

Источник для проверки: [TEGAM 3550 manual на ManualsLib](https://www.manualslib.com/manual/1356020/Tegam-3550.html), раздел RS-232C command summary.

## Про реле/SSR

Код учитывает реле как внешний исполнительный элемент, подключенный к GPIO Raspberry Pi:

```text
Raspberry Pi GPIO -> driver/opto -> SSR или relay -> печь
```

В конфиге это блок:

```toml
[heater]
gpio_pin = 17
active_high = true
cycle_s = 5.0
```

Код не управляет внутренними аппаратными реле Agilent/TEGAM и не заменяет аппаратный аварийный термостат. Software safety только дополнение. Силовая часть печи должна иметь независимый аппаратный cut-off.

## Запуск как service

Шаблон лежит в `systemd/furnacepi.service`.

```bash
sudo cp systemd/furnacepi.service /etc/systemd/system/furnacepi.service
sudo systemctl daemon-reload
sudo systemctl enable furnacepi.service
sudo systemctl start furnacepi.service
sudo journalctl -u furnacepi.service -f
```

Перед `systemctl start` обязательно проверьте `config.real.toml`.
