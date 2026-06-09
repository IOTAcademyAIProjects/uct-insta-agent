#!/bin/bash
echo "Setting up uct-insta-agent..."

# Install OpenClaw
npm install -g openclaw

# Install project dependencies
npm install

echo "Done! Now fill in your .env file:"
cp .env.example .env
echo "Run: nano .env or vi .env to add your keys"
