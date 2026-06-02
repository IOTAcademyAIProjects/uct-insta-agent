# Telegram Bot Setup Guide

## Bot details
- Name: UCT ClawGram
- Username: @uct_clawgram_bot
- Created via: @BotFather

## Important
Bot is already created. Do NOT create a new bot.
Get the token privately from Abhishek.
Never commit the token to GitHub.

## Pairing steps
1. Run: openclaw gateway run
2. Open Telegram, search @uct_clawgram_bot, send /start
3. Copy the pairing code from bot
4. Run: openclaw pairing approve telegram YOUR_CODE
5. Share your Telegram ID with Abhishek

## Approved IDs
- Abhishek: 8909720609
- Drupad: TBD after pairing

## Adding new member
Run on Lightning.ai:
openclaw config set channels.telegram.allowFrom '["8909720609","NEW_ID"]'

## Bot commands
- /start initialize bot
- /help show commands
- /new new session
- /reset reset session

## Security rules
- dmPolicy must stay as allowlist
- Never set dmPolicy to open
- Rotate token before M11
- Run openclaw security audit regularly

## Troubleshooting
- Bot silent: gateway not running
- Code rejected: restart gateway
- Not authorized: ask Abhishek to add your ID
