# Deployment Guide for chatwithgithub.pratikpdl.com.np

## Docker Deployment (Recommended)

### Prerequisites

1. VPS with Ubuntu 20.04+ at IP: 194.163.172.56
2. Domain: chatwithgithub.pratikpdl.com.np pointing to your VPS IP
3. SSH access to your VPS
4. Groq API key

### Quick Start

**1. Configure DNS**

Point your domain to your VPS:
- Create an A record for `chatwithgithub.pratikpdl.com.np` → `194.163.172.56`
- Wait for DNS propagation (can take up to 24 hours, usually much faster)

Verify DNS:
```bash
nslookup chatwithgithub.pratikpdl.com.np
```

**2. Copy Files to VPS**

From your local machine:
```bash
# Copy all files to VPS
scp -r . root@194.163.172.56:/opt/chatwithgithub/

# SSH into VPS
ssh root@194.163.172.56
```

**3. Deploy with Docker**

On your VPS:
```bash
cd /opt/chatwithgithub

# Update .env with your actual API key
nano .env

# Make deploy script executable
chmod +x docker-deploy.sh

# Run deployment
sudo ./docker-deploy.sh
```

That's it! The script will:
- Install Docker and Docker Compose
- Build your application container
- Set up Nginx reverse proxy
- Configure SSL with Let's Encrypt
- Start all services

Your app will be live at `https://chatwithgithub.pratikpdl.com.np`

### Docker Commands

```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs -f

# View app logs only
docker-compose logs -f app

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Rebuild and restart
docker-compose up -d --build

# Remove everything (including volumes)
docker-compose down -v
```

### Updating Your Application

When you make changes:

```bash
# On local machine
scp -r . root@194.163.172.56:/opt/chatwithgithub/

# On VPS
cd /opt/chatwithgithub
docker-compose down
docker-compose up -d --build
```

### Manual Docker Setup

If you prefer step-by-step:

**1. Install Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo systemctl start docker
sudo systemctl enable docker
```

**2. Install Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**3. Build and Run**
```bash
cd /opt/chatwithgithub

# Start without SSL first
docker-compose up -d app

# Setup SSL
chmod +x init-letsencrypt.sh
./init-letsencrypt.sh

# Start all services
docker-compose up -d
```

---

## Traditional Deployment (Without Docker)

### Step 1: Configure DNS

Point your domain to your VPS:
- Create an A record for `chatwithgithub.pratikpdl.com.np` → `194.163.172.56`
- Wait for DNS propagation (can take up to 24 hours, usually much faster)

Verify DNS:
```bash
nslookup chatwithgithub.pratikpdl.com.np
```

## Step 2: Prepare Your Local Files

1. Update `.env` file with your actual Groq API key
2. Make sure all your code is ready

## Step 3: Transfer Files to VPS

From your local machine:

```bash
# Create a tarball of your project (excluding unnecessary files)
tar -czf chatwithgithub.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='chroma_db' \
  --exclude='.git' \
  --exclude='venv' \
  .

# Copy to VPS
scp chatwithgithub.tar.gz root@194.163.172.56:/tmp/

# SSH into VPS
ssh root@194.163.172.56
```

## Step 4: Deploy on VPS

On your VPS:

```bash
# Create application directory
sudo mkdir -p /var/www/chatwithgithub
cd /var/www/chatwithgithub

# Extract files
sudo tar -xzf /tmp/chatwithgithub.tar.gz -C /var/www/chatwithgithub

# Make deploy script executable
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

The script will:
- Install Python, Nginx, and dependencies
- Set up virtual environment
- Install Python packages
- Create systemd service
- Configure Nginx
- Set up SSL certificate with Let's Encrypt
- Configure firewall

## Step 5: Configure Environment Variables

Edit the `.env` file with your actual values:

```bash
cd /var/www/chatwithgithub
nano .env
```

Update:
- `GROQ_API_KEY` with your actual API key
- Any other settings as needed

Then restart the service:

```bash
sudo systemctl restart chatwithgithub
```

## Step 6: Verify Deployment

Check service status:
```bash
sudo systemctl status chatwithgithub
```

View logs:
```bash
sudo journalctl -u chatwithgithub -f
```

Test the application:
```bash
curl http://localhost:8000/health
```

Visit your domain:
- http://chatwithgithub.pratikpdl.com.np (will redirect to HTTPS)
- https://chatwithgithub.pratikpdl.com.np

## Manual Deployment (Alternative)

If you prefer manual setup:

### 1. Install Dependencies

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx
```

### 2. Setup Application

```bash
cd /var/www/chatwithgithub
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Create Systemd Service

Create `/etc/systemd/system/chatwithgithub.service`:

```ini
[Unit]
Description=Chat with GitHub - FastAPI Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/chatwithgithub
Environment="PATH=/var/www/chatwithgithub/venv/bin"
ExecStart=/var/www/chatwithgithub/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable chatwithgithub
sudo systemctl start chatwithgithub
```

### 4. Configure Nginx

Create `/etc/nginx/sites-available/chatwithgithub`:

```nginx
server {
    listen 80;
    server_name chatwithgithub.pratikpdl.com.np;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location /static {
        alias /var/www/chatwithgithub/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/chatwithgithub /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Setup SSL

```bash
sudo certbot --nginx -d chatwithgithub.pratikpdl.com.np
```

### 6. Configure Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Useful Commands

### Service Management
```bash
# Check status
sudo systemctl status chatwithgithub

# Start service
sudo systemctl start chatwithgithub

# Stop service
sudo systemctl stop chatwithgithub

# Restart service
sudo systemctl restart chatwithgithub

# View logs
sudo journalctl -u chatwithgithub -f

# View last 100 lines
sudo journalctl -u chatwithgithub -n 100
```

### Nginx Management
```bash
# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx

# View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Application Updates

When you need to update the application:

```bash
# On your local machine, create new tarball
tar -czf chatwithgithub.tar.gz \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='chroma_db' \
  --exclude='.git' \
  --exclude='venv' \
  .

# Copy to VPS
scp chatwithgithub.tar.gz root@194.163.172.56:/tmp/

# On VPS
cd /var/www/chatwithgithub
sudo systemctl stop chatwithgithub
sudo tar -xzf /tmp/chatwithgithub.tar.gz
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl start chatwithgithub
```

## Troubleshooting

### Service won't start
```bash
# Check logs
sudo journalctl -u chatwithgithub -n 50

# Check if port 8000 is in use
sudo netstat -tulpn | grep 8000

# Test manually
cd /var/www/chatwithgithub
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Nginx errors
```bash
# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Test configuration
sudo nginx -t
```

### SSL certificate issues
```bash
# Renew certificate manually
sudo certbot renew

# Test renewal
sudo certbot renew --dry-run
```

### Database cleanup
The application automatically cleans up old ChromaDB files after 1 hour. You can also manually trigger cleanup:

```bash
curl -X POST http://localhost:8000/api/cleanup
```

## Security Recommendations

1. Change default SSH port
2. Set up SSH key authentication and disable password login
3. Configure fail2ban
4. Regular system updates
5. Monitor logs regularly
6. Set up backup for important data
7. Use environment variables for sensitive data (already done)

## Monitoring

Consider setting up:
- Uptime monitoring (UptimeRobot, Pingdom)
- Log aggregation (ELK stack, Graylog)
- Performance monitoring (New Relic, DataDog)

## Backup

Important directories to backup:
- `/var/www/chatwithgithub/.env` (environment variables)
- `/var/www/chatwithgithub/chroma_db` (if you want to persist databases)

## Support

If you encounter issues:
1. Check service logs: `sudo journalctl -u chatwithgithub -f`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify DNS configuration
4. Ensure firewall allows traffic on ports 80 and 443
