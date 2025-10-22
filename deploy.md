# Deployment Guide

This guide shows you how to deploy the Trading Bot on different platforms and environments.

## 🚀 Quick Start (Local Development)

### Windows
```bash
# Double-click run.bat or run in command prompt
run.bat
```

### macOS/Linux
```bash
# Make executable and run
chmod +x run.sh
./run.sh
```

### Manual Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py web
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)
```bash
# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# Stop
docker-compose down
```

### Using Docker directly
```bash
# Build image
docker build -t trading-bot .

# Run container
docker run -p 5000:5000 trading-bot
```

## ☁️ Cloud Deployment

### Heroku
1. Create `Procfile`:
```
web: python main.py web --host 0.0.0.0 --port $PORT
```

2. Deploy:
```bash
heroku create your-trading-bot
git push heroku main
```

### AWS EC2
1. Launch Ubuntu instance
2. Install Docker:
```bash
sudo apt update
sudo apt install docker.io docker-compose
```

3. Clone and run:
```bash
git clone <your-repo>
cd Bot
docker-compose up -d
```

### Google Cloud Platform
1. Create Cloud Run service
2. Build and deploy:
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/trading-bot
gcloud run deploy --image gcr.io/PROJECT-ID/trading-bot
```

## 🔧 Environment Configuration

### Production Settings
Create `.env` file:
```env
FLASK_ENV=production
FLASK_DEBUG=False
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://host:port
```

### Development Settings
```env
FLASK_ENV=development
FLASK_DEBUG=True
```

## 📊 Monitoring and Logging

### Health Checks
- Web interface: `http://localhost:5000`
- API status: `http://localhost:5000/api/status`

### Logs
```bash
# Docker logs
docker-compose logs -f

# Application logs
tail -f logs/trading-bot.log
```

## 🔒 Security Considerations

### Production Checklist
- [ ] Use environment variables for secrets
- [ ] Enable HTTPS/SSL
- [ ] Set up firewall rules
- [ ] Use production database
- [ ] Implement rate limiting
- [ ] Add authentication if needed

### Network Security
```bash
# Firewall rules (Ubuntu)
sudo ufw allow 5000
sudo ufw enable
```

## 📈 Scaling

### Horizontal Scaling
- Use load balancer (nginx, HAProxy)
- Multiple instances behind proxy
- Database clustering for high availability

### Vertical Scaling
- Increase server resources
- Optimize database queries
- Use caching (Redis)

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**
```bash
# Find process using port 5000
netstat -tulpn | grep :5000
# Kill process
kill -9 <PID>
```

2. **Dependencies issues**
```bash
# Rebuild virtual environment
rm -rf .venv
python -m venv .venv
pip install -r requirements.txt
```

3. **Docker issues**
```bash
# Clean up Docker
docker system prune -a
docker-compose down -v
docker-compose up --build
```

### Performance Optimization
- Use production WSGI server (Gunicorn)
- Enable caching
- Optimize database queries
- Use CDN for static files

## 📋 Maintenance

### Regular Tasks
- Update dependencies monthly
- Monitor system resources
- Backup database
- Review logs for errors

### Updates
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart services
docker-compose restart
```

---

**Need help?** Check the main README.md or create an issue in the repository.
