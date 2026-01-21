#!/bin/bash

# Deployment script for chatwithgithub.pratikpdl.com.np
# Run this script on your VPS at 194.163.172.56

set -e

echo "Starting deployment..."

# Update system
echo "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
echo "Installing Python and dependencies..."
sudo apt install -y python3.11 python3.11-venv python3-pip git nginx certbot python3-certbot-nginx

# Create application directory
APP_DIR="/var/www/chatwithgithub"
echo "Setting up application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown -R $USER:$USER $APP_DIR

# Clone or update repository (if using git)
# cd $APP_DIR
# git clone <your-repo-url> .

# Create virtual environment
echo "Creating virtual environment..."
cd $APP_DIR
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p chroma_db
mkdir -p static

# Copy environment file
echo "Setting up environment variables..."
cp .env.example .env
echo "Please edit $APP_DIR/.env with your actual API keys"

# Create systemd service
echo "Creating systemd service..."
sudo tee /etc/systemd/system/chatwithgithub.service > /dev/null <<EOF
[Unit]
Description=Chat with GitHub - FastAPI Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Configure Nginx
echo "Configuring Nginx..."
sudo tee /etc/nginx/sites-available/chatwithgithub > /dev/null <<'EOF'
server {
    listen 80;
    server_name chatwithgithub.pratikpdl.com.np;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts for long-running requests
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/chatwithgithub /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t

# Reload systemd and start services
echo "Starting services..."
sudo systemctl daemon-reload
sudo systemctl enable chatwithgithub
sudo systemctl start chatwithgithub
sudo systemctl restart nginx

# Setup SSL with Let's Encrypt
echo "Setting up SSL certificate..."
echo "Make sure your domain chatwithgithub.pratikpdl.com.np points to 194.163.172.56"
read -p "Press enter when DNS is configured to continue with SSL setup..."

sudo certbot --nginx -d chatwithgithub.pratikpdl.com.np --non-interactive --agree-tos --email your-email@example.com

# Setup firewall
echo "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo "Deployment complete!"
echo "Your application should be running at https://chatwithgithub.pratikpdl.com.np"
echo ""
echo "Useful commands:"
echo "  - Check service status: sudo systemctl status chatwithgithub"
echo "  - View logs: sudo journalctl -u chatwithgithub -f"
echo "  - Restart service: sudo systemctl restart chatwithgithub"
echo "  - Check Nginx: sudo nginx -t"
