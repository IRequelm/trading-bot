#!/bin/bash

echo "========================================"
echo "   GITHUB SETUP FOR IRequelm"
echo "========================================"
echo

echo "Setting up your trading bot on GitHub..."
echo

echo "Step 1: Create GitHub Repository"
echo "================================"
echo "1. Go to https://github.com/IRequelm"
echo "2. Click 'New repository' (green button)"
echo "3. Repository name: trading-bot"
echo "4. Description: 'Advanced Trading Bot with Backtesting'"
echo "5. Make it Public (so you can use free Codespaces)"
echo "6. DON'T check 'Initialize with README' (we have our own)"
echo "7. Click 'Create repository'"
echo

echo "Step 2: Run these commands in your project folder"
echo "================================================"
echo

echo "git init"
git init

echo
echo "git add ."
git add .

echo
echo "git commit -m 'Initial trading bot project'"
git commit -m "Initial trading bot project"

echo
echo "git branch -M main"
git branch -M main

echo
echo "git remote add origin https://github.com/IRequelm/trading-bot.git"
git remote add origin https://github.com/IRequelm/trading-bot.git

echo
echo "git push -u origin main"
git push -u origin main

echo
echo "========================================"
echo "   SETUP COMPLETE!"
echo "========================================"
echo
echo "Your trading bot is now on GitHub!"
echo
echo "Next steps:"
echo "1. Go to https://github.com/IRequelm/trading-bot"
echo "2. Click 'Code' → 'Codespaces' → 'Create codespace'"
echo "3. Work from any computer in the cloud!"
echo
echo "Repository URL: https://github.com/IRequelm/trading-bot"
echo
