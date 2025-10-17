# BMW Parser Bot

Telegram bot for monitoring new BMW vehicles on the official website and sending notifications to chat.

> **Русская версия**: [README.md](README.md)

## 🚀 Features

- **Real-time monitoring**: Continuous tracking of new BMW vehicles
- **Telegram notifications**: Instant notifications about new lots with photos
- **Google Sheets integration**: Automatic saving of all data to spreadsheet
- **Deduplication**: Automatic removal of duplicates
- **Administrative commands**: Bot management through Telegram

## 📋 Bot Commands

- `/status` - Show status of the last monitoring cycle
- `/logs` - Send full work log
- `/errors` - Send error log
- `/restart` - Restart the bot (admin only)

## 🛠️ Installation and Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd bmw-bot
```

### 2. Create virtual environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r app/requirements.txt
```

### 4. Configure environment variables

Copy `env_template.txt` to `.env` and fill in your data:

```bash
cp env_template.txt .env
```

Edit the `.env` file:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_token_from_BotFather
CHAT_IDS=chat_id1,chat_id2,chat_id3
ADMIN_IDS=admin_id1,admin_id2

# Monitoring Configuration
POLL_INTERVAL=60

# Google Sheets Configuration
GS_CRED=bmwparser111-4e64ca22a559.json
GSHEET_NAME=your_spreadsheet_name
```

### 5. Google Sheets Setup

1. Create a new project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Google Sheets API and Google Drive API
3. Create a Service Account and download the JSON key
4. Place the JSON file in the `creds/` folder
5. Create a Google Sheet and share it with the email from the JSON key
6. Update `GS_CRED` and `GSHEET_NAME` in `.env`

### 6. Create Telegram Bot

1. Write to [@BotFather](https://t.me/BotFather) in Telegram
2. Create a new bot with `/newbot`
3. Copy the token to `BOT_TOKEN`
4. Add the bot to the required chats
5. Get chat IDs (you can use [@userinfobot](https://t.me/userinfobot))

### 7. Run

```bash
cd app
python bmw_bot.py
```

## 📊 Google Sheets Structure

The bot will automatically create the following columns in the spreadsheet:

| Column | Description |
|--------|-------------|
| vssId | Unique vehicle ID |
| model | Model and options |
| price | Price in euros |
| mileage | Mileage in km |
| gearbox | Transmission type |
| fuel | Fuel type |
| url | Link to the card |
| date_added | Date added |

## ⚙️ Parsing Filter Configuration

Filters are configured in the `build_beta_filters()` function in `bmw_bot.py` (lines 220-230).

### Current Filters:

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

### Filter Configuration:

#### 1. Vehicle Models
```python
"model": {"marketingModelRange": {"value": ["X3_G01", "X5_G05", "3_G20"]}}
```

Available models:
- `X3_G01` - BMW X3
- `X5_G05` - BMW X5  
- `3_G20` - BMW 3 Series
- `5_G30` - BMW 5 Series
- `X1_F48` - BMW X1
- And others...

#### 2. Fuel Type
```python
"degreeOfElectrificationBasedFuelType": {"value": ["DIESEL", "GASOLINE", "HYBRID", "ELECTRIC"]}
```

#### 3. Power (in hp)
```python
"technicalData": {"powerBasedOnDegreeOfElectrificationPs": [{"minValue": 150, "maxValue": 300}]}
```

#### 4. Mileage (in km)
```python
"usedCarData": {"mileageRanges": [{"minValue": 0, "maxValue": 100000}]}
```

#### 5. Registration Year
```python
"initialRegistrationDateRanges": [{"minValue": "2020-01-01", "maxValue": "2024-12-31"}]
```

#### 6. Sorting
```python
"resultsContext": {"sort": [{"by": "PRODUCTION_DATE", "order": "DESC"}]}
```

Available sorting options:
- `PRODUCTION_DATE` - by production date
- `PRICE` - by price
- `MILEAGE` - by mileage
- `POWER` - by power
- `DESC` - descending
- `ASC` - ascending

### Example Configuration for BMW X5 with Diesel Engine:

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

## 📁 Project Structure

```
bmw-bot/
├── app/
│   ├── bmw_bot.py          # Main bot code
│   └── requirements.txt    # Python dependencies
├── creds/                  # Folder for Google Sheets keys (not in git)
├── logs/                   # Work logs (not in git)
├── venv/                   # Virtual environment (not in git)
├── .gitignore             # Git exclusions
├── env_template.txt       # Environment variables template
└── README_EN.md           # Documentation (English)
```

## 🔒 Security

- All sensitive data (`.env`, `creds/`, `logs/`) excluded from git
- Use `.gitignore` to prevent accidental data publication
- Never commit tokens or keys to the repository

## 🐛 Troubleshooting

### Bot won't start
1. Check the token correctness in `.env`
2. Make sure all dependencies are installed
3. Check Google Sheets access rights

### No notifications received
1. Check the correctness of `CHAT_IDS`
2. Make sure the bot is added to chats
3. Check logs: `/logs` or `/errors`

### Google Sheets errors
1. Check the correctness of the JSON key
2. Make sure the spreadsheet is accessible to the Service Account
3. Check the spreadsheet name in `GSHEET_NAME`

## 📝 Logging

The bot keeps detailed logs:
- `logs/app.log` - general work logs
- `logs/errors.log` - errors only

Logs are rotated daily and stored for 14 days.

## 🔄 Automatic Startup

For automatic startup on a server, it's recommended to use systemd or supervisor.

Example systemd service:

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

## 📞 Support

If you encounter problems, check:
1. Bot logs via `/logs` command
2. Environment variables in `.env`
3. Google Sheets API availability
4. Network connections
