# 🔒 Security Guide - Safe GitHub Publishing

This guide will help you safely publish your BMW Parser Bot to GitHub without exposing sensitive data.

## ✅ What's Already Protected

The following files and folders are **automatically excluded** from Git thanks to `.gitignore`:

- `.env` - Your environment variables with tokens
- `creds/` - Google Sheets credentials (JSON files)
- `logs/` - Log files
- `venv/` - Python virtual environment
- All temporary and system files

## 🚀 Steps to Publish Safely

### 1. Verify Protection

Check what files Git will track:

```bash
cd /Users/uran_favor/Desktop/bmw-bot
git status
```

You should see **ONLY** these files:
- `README.md`
- `README_EN.md` 
- `SECURITY_GUIDE.md`
- `.gitignore`
- `app/bmw_bot.py`
- `app/requirements.txt`
- `app/env_template.txt`

### 2. Initialize Git Repository

```bash
git init
git add .
git commit -m "Initial commit: BMW Parser Bot with English translation"
```

### 3. Create GitHub Repository

1. Go to [GitHub.com](https://github.com)
2. Click "New repository"
3. Name it `bmw-parser-bot` (or any name you prefer)
4. **DO NOT** initialize with README, .gitignore, or license
5. Click "Create repository"

### 4. Connect and Push

```bash
git remote add origin https://github.com/YOUR_USERNAME/bmw-parser-bot.git
git branch -M main
git push -u origin main
```

## 🔐 What You Need to Do After Cloning

Anyone who clones your repository will need to:

### 1. Create `.env` File

Copy the template and fill in your data:

```bash
cp app/env_template.txt .env
```

Edit `.env` with your actual values:
- `BOT_TOKEN` - Your Telegram bot token
- `CHAT_IDS` - Comma-separated chat IDs
- `ADMIN_IDS` - Comma-separated admin user IDs
- `GSHEET_NAME` - Your Google Sheet name

### 2. Add Google Sheets Credentials

1. Create a folder `creds/`
2. Place your Google Sheets JSON key file in `creds/`
3. Update `GS_CRED` in `.env` to match your filename

### 3. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r app/requirements.txt
```

## ⚠️ Important Security Notes

1. **Never commit sensitive files** - Always check `git status` before committing
2. **Rotate credentials** - If you accidentally commit sensitive data, immediately:
   - Delete the repository
   - Generate new tokens/keys
   - Create a new repository
3. **Use environment variables** - Never hardcode tokens in source code
4. **Review before publishing** - Always review what you're about to push

## 🔍 Double-Check Before Publishing

Run this command to see exactly what will be published:

```bash
git ls-files
```

This should show only safe files. If you see any of these, **STOP** and fix `.gitignore`:
- `.env`
- `creds/`
- `logs/`
- `venv/`
- Any `.json` files with credentials

## 🆘 If You Accidentally Commit Sensitive Data

1. **Immediately** revoke all exposed tokens/keys
2. Remove sensitive data from Git history:
   ```bash
   git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch creds/*.json .env' --prune-empty --tag-name-filter cat -- --all
   ```
3. Force push:
   ```bash
   git push origin --force --all
   ```
4. Generate new credentials and update your local `.env`

## ✅ Final Verification

After publishing, verify your repository is safe:

1. Check that sensitive files are not visible on GitHub
2. Test cloning your repository to a new location
3. Verify that `.env` and `creds/` folders are missing
4. Confirm that `env_template.txt` is present as a guide

Your repository is now safe to share! 🎉
