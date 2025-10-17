# BMW Parser Bot

Telegram-бот для мониторинга новых автомобилей BMW на официальном сайте и отправки уведомлений в чат.

> **English version**: [README_EN.md](README_EN.md)

## 🚀 Функциональность

- **Мониторинг в реальном времени**: Постоянное отслеживание новых автомобилей BMW
- **Telegram уведомления**: Мгновенные уведомления о новых лотах с фотографиями
- **Google Sheets интеграция**: Автоматическое сохранение всех данных в таблицу
- **Дедупликация**: Автоматическое удаление дубликатов
- **Административные команды**: Управление ботом через Telegram

## 📋 Команды бота

- `/status` - Показать статус последнего цикла мониторинга
- `/logs` - Отправить полный лог работы
- `/errors` - Отправить лог ошибок
- `/restart` - Перезапустить бота (только для админов)

## 🛠️ Установка и настройка

### 1. Клонирование репозитория

```bash
git clone <your-repo-url>
cd bmw-bot
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # На Windows: venv\Scripts\activate
```

### 3. Установка зависимостей

```bash
pip install -r app/requirements.txt
```

### 4. Настройка переменных окружения

Скопируйте `env_template.txt` в `.env` и заполните своими данными:

```bash
cp env_template.txt .env
```

Отредактируйте `.env` файл:

```env
# Telegram Bot Configuration
BOT_TOKEN=ваш_токен_от_BotFather
CHAT_IDS=ID_чата1,ID_чата2,ID_чата3
ADMIN_IDS=ID_админа1,ID_админа2

# Monitoring Configuration
POLL_INTERVAL=60

# Google Sheets Configuration
GS_CRED=bmwparser111-4e64ca22a559.json
GSHEET_NAME=название_вашей_таблицы
```

### 5. Настройка Google Sheets

1. Создайте новый проект в [Google Cloud Console](https://console.cloud.google.com/)
2. Включите Google Sheets API и Google Drive API
3. Создайте Service Account и скачайте JSON ключ
4. Поместите JSON файл в папку `creds/`
5. Создайте Google Sheet и поделитесь ей с email из JSON ключа
6. Обновите `GS_CRED` и `GSHEET_NAME` в `.env`

### 6. Создание Telegram бота

1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. Создайте нового бота командой `/newbot`
3. Скопируйте токен в `BOT_TOKEN`
4. Добавьте бота в нужные чаты
5. Получите ID чатов (можно через [@userinfobot](https://t.me/userinfobot))

### 7. Запуск

```bash
cd app
python bmw_bot.py
```

## 📊 Структура Google Sheets

Бот автоматически создаст следующие колонки в таблице:

| Колонка | Описание |
|---------|----------|
| vssId | Уникальный ID автомобиля |
| model | Модель и опции |
| price | Цена в евро |
| mileage | Пробег в км |
| gearbox | Тип коробки передач |
| fuel | Тип топлива |
| url | Ссылка на карточку |
| date_added | Дата добавления |

## ⚙️ Настройка фильтров парсинга

Фильтры настраиваются в функции `build_beta_filters()` в файле `bmw_bot.py` (строки 229-239).

### Текущие фильтры:

```python
def build_beta_filters() -> dict:
    return {
        "searchContext": [{
            "model": {"marketingModelRange": {"value": ["X3_G01"]}},
            "degreeOfElectrificationBasedFuelType": {"value": ["DIESEL", "GASOLINE"]},
            "technicalData": {"powerBasedOnDegreeOfElectrificationPs": [{"maxValue": 200}]},
            "usedCarData": {"mileageRanges": [{"minValue": 0, "maxValue": 60000}]},
            "initialRegistrationDateRanges": [{"minValue": "2021-01-01", "maxValue": "2022-12-31"}]
        }],
        "resultsContext": {"sort": [{"by": "PRODUCTION_DATE", "order": "DESC"}]}
    }
```

### Настройка фильтров:

#### 1. Модели автомобилей
```python
"model": {"marketingModelRange": {"value": ["X3_G01", "X5_G05", "3_G20"]}}
```

Доступные модели:
- `X3_G01` - BMW X3
- `X5_G05` - BMW X5  
- `3_G20` - BMW 3 Series
- `5_G30` - BMW 5 Series
- `X1_F48` - BMW X1
- И другие...

#### 2. Тип топлива
```python
"degreeOfElectrificationBasedFuelType": {"value": ["DIESEL", "GASOLINE", "HYBRID", "ELECTRIC"]}
```

#### 3. Мощность (в л.с.)
```python
"technicalData": {"powerBasedOnDegreeOfElectrificationPs": [{"minValue": 150, "maxValue": 300}]}
```

#### 4. Пробег (в км)
```python
"usedCarData": {"mileageRanges": [{"minValue": 0, "maxValue": 100000}]}
```

#### 5. Год регистрации
```python
"initialRegistrationDateRanges": [{"minValue": "2020-01-01", "maxValue": "2024-12-31"}]
```

#### 6. Сортировка
```python
"resultsContext": {"sort": [{"by": "PRODUCTION_DATE", "order": "DESC"}]}
```

Доступные варианты сортировки:
- `PRODUCTION_DATE` - по дате производства
- `PRICE` - по цене
- `MILEAGE` - по пробегу
- `POWER` - по мощности
- `DESC` - по убыванию
- `ASC` - по возрастанию

### Пример настройки для поиска BMW X5 с дизельным двигателем:

```python
def build_beta_filters() -> dict:
    return {
        "searchContext": [{
            "model": {"marketingModelRange": {"value": ["X5_G05"]}},
            "degreeOfElectrificationBasedFuelType": {"value": ["DIESEL"]},
            "technicalData": {"powerBasedOnDegreeOfElectrificationPs": [{"minValue": 200, "maxValue": 400}]},
            "usedCarData": {"mileageRanges": [{"minValue": 0, "maxValue": 80000}]},
            "initialRegistrationDateRanges": [{"minValue": "2020-01-01", "maxValue": "2023-12-31"}]
        }],
        "resultsContext": {"sort": [{"by": "PRICE", "order": "ASC"}]}
    }
```

## 📁 Структура проекта

```
bmw-bot/
├── app/
│   ├── bmw_bot.py          # Основной код бота
│   └── requirements.txt    # Зависимости Python
├── creds/                  # Папка для Google Sheets ключей (не в git)
├── logs/                   # Логи работы (не в git)
├── venv/                   # Виртуальное окружение (не в git)
├── .gitignore             # Исключения для git
├── env_template.txt       # Шаблон переменных окружения
└── README.md              # Документация
```

## 🔒 Безопасность

- Все чувствительные данные (`.env`, `creds/`, `logs/`) исключены из git
- Используйте `.gitignore` для предотвращения случайной публикации данных
- Никогда не коммитьте токены или ключи в репозиторий

## 🐛 Решение проблем

### Бот не запускается
1. Проверьте правильность токена в `.env`
2. Убедитесь, что установлены все зависимости
3. Проверьте права доступа к Google Sheets

### Не приходят уведомления
1. Проверьте правильность `CHAT_IDS`
2. Убедитесь, что бот добавлен в чаты
3. Проверьте логи: `/logs` или `/errors`

### Ошибки Google Sheets
1. Проверьте правильность JSON ключа
2. Убедитесь, что таблица доступна для Service Account
3. Проверьте название таблицы в `GSHEET_NAME`

## 📝 Логирование

Бот ведет подробные логи:
- `logs/app.log` - общие логи работы
- `logs/errors.log` - только ошибки

Логи ротируются ежедневно и хранятся 14 дней.

## 🔄 Автоматический запуск

Для автоматического запуска на сервере рекомендуется использовать systemd или supervisor.

Пример systemd сервиса:

```ini
[Unit]
Description=BMW Parser Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bmw-bot/app
ExecStart=/path/to/bmw-bot/venv/bin/python bmw_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📞 Поддержка

При возникновении проблем проверьте:
1. Логи бота через команду `/logs`
2. Переменные окружения в `.env`
3. Доступность Google Sheets API
4. Сетевые подключения
