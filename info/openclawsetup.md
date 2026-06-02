# OpenClaw Setup Guide

## Prerequisites
- Node.js v18+
- Git
- Anthropic API key
- Telegram account

## Step 1 Clone the repo
git clone https://github.com/IOTAcademyAIProjects/uct-insta-agent.git
cd uct-insta-agent
git checkout -b your-name

## Step 2 Install OpenClaw
node --version
npm install -g openclaw
openclaw --version

## Step 3 Run onboard
openclaw onboard
- Security disclaimer: Y
- Setup mode: QuickStart
- Provider: Anthropic
- Auth: Anthropic API key
- Model: claude-haiku-4-5
- Channel: Telegram
- Token: get from Abhishek privately
- Web search: Skip
- Skills: gemini
- Hooks: session-memory
- Hatch: Hatch in Terminal

## Step 4 Start gateway
openclaw gateway run

## Step 5 Pair Telegram
openclaw pairing approve telegram YOUR_CODE

## Step 6 Install skills
openclaw skills install gemini
openclaw skills install video-frames

## Troubleshooting
- command not found: npm install -g openclaw
- bot not responding: check gateway is running
- pairing fails: restart gateway and retry
- node too old: nvm install 18 and nvm use 18
