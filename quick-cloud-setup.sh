#!/bin/bash

echo "========================================"
echo "   TRADING BOT - CLOUD SETUP WIZARD"
echo "========================================"
echo
echo "This will help you set up your trading bot in the cloud"
echo "so you can work from any computer without carrying anything."
echo

echo "Choose your preferred cloud platform:"
echo
echo "1. GitHub + Codespaces (Recommended - Free, Professional)"
echo "2. Replit (Easiest - Free, No setup needed)"
echo "3. Google Colab + Drive (Free, Good for testing)"
echo "4. GitPod (Professional IDE in browser)"
echo

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        echo
        echo "========================================"
        echo "   GITHUB + CODESPACES SETUP"
        echo "========================================"
        echo
        echo "1. Go to https://github.com and create a new repository"
        echo "2. Name it 'trading-bot' (or any name you prefer)"
        echo "3. Make it public or private (your choice)"
        echo "4. Don't initialize with README (we have our own)"
        echo
        echo "After creating the repository, run these commands:"
        echo
        echo "git init"
        echo "git add ."
        echo "git commit -m 'Initial trading bot project'"
        echo "git remote add origin https://github.com/YOUR_USERNAME/trading-bot.git"
        echo "git push -u origin main"
        echo
        echo "Then go to https://github.com/codespaces to access your project from anywhere!"
        ;;
    2)
        echo
        echo "========================================"
        echo "   REPLIT SETUP"
        echo "========================================"
        echo
        echo "1. Go to https://replit.com"
        echo "2. Sign up or log in"
        echo "3. Click 'Create Repl'"
        echo "4. Choose 'Python' template"
        echo "5. Name it 'trading-bot'"
        echo "6. Upload all your project files"
        echo "7. Run: python main.py web"
        echo
        echo "That's it! Your bot is now in the cloud!"
        ;;
    3)
        echo
        echo "========================================"
        echo "   GOOGLE COLAB + DRIVE SETUP"
        echo "========================================"
        echo
        echo "1. Upload your project folder to Google Drive"
        echo "2. Go to https://colab.research.google.com"
        echo "3. Create new notebook"
        echo "4. Mount Google Drive:"
        echo "   from google.colab import drive"
        echo "   drive.mount('/content/drive')"
        echo "5. Navigate to your project and run it"
        echo
        echo "Note: This is best for testing, not full development"
        ;;
    4)
        echo
        echo "========================================"
        echo "   GITPOD SETUP"
        echo "========================================"
        echo
        echo "1. First set up GitHub repository (see option 1)"
        echo "2. Go to https://gitpod.io"
        echo "3. Enter your GitHub repository URL"
        echo "4. Click 'Open in GitPod'"
        echo "5. Wait for environment to load"
        echo "6. Run: python main.py web"
        echo
        echo "Professional IDE in your browser!"
        ;;
    *)
        echo "Invalid choice. Please run the script again."
        exit 1
        ;;
esac

echo
echo "========================================"
echo "   CLOUD SETUP COMPLETE!"
echo "========================================"
echo
echo "Your trading bot is now accessible from anywhere!"
echo "No more carrying files or setting up environments."
echo
echo "Happy coding! 🚀"
echo
