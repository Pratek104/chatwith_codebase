#!/bin/bash

# Docker deployment script for chatwithgithub.pratikpdl.com.np
# Run this on your VPS at 194.163.172.56

set -e

echo "=== Docker Deployment for Chat with GitHub ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root or with sudo"
  exit 1
fi

# Update system
echo "Step 1: Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "Step 2: Installing Docker..."
    apt-get install -y ca-certificates curl gnupg lsb-release
    
    # Add Docker's official GPG key
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Install Docker Engine
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    echo "Docker installed successfully!"
else
    echo "Step 2: Docker is already installed"
fi

# Install Docker Compose (standalone)
if ! command -v docker-compose &> /dev/null; then
    echo "Step 3: Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "Docker Compose installed successfully!"
else
    echo "Step 3: Docker Compose is already installed"
fi

# Create application directory
APP_DIR="/opt/chatwithgithub"
echo "Step 4: Setting up application directory at $APP_DIR..."
mkdir -p $APP_DIR
cd $APP_DIR

# Check if files are already here
if [ ! -f "docker-compose.yml" ]; then
    echo "Please copy your application files to $APP_DIR first!"
    echo "Run this on your local machine:"
    echo "  scp -r . root@194.163.172.56:$APP_DIR/"
    exit 1
fi

# Create necessary directories
echo "Step 5: Creating necessary directories..."
mkdir -p chroma_db
mkdir -p static
mkdir -p certbot/conf
mkdir -p certbot/www

# Check .env file
if [ ! -f ".env" ]; then
    echo "Step 6: Creating .env file..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit $APP_DIR/.env with your actual API keys!"
    echo "Run: nano $APP_DIR/.env"
    read -p "Press enter after you've updated the .env file..."
else
    echo "Step 6: .env file already exists"
fi

# Make scripts executable
echo "Step 7: Making scripts executable..."
chmod +x init-letsencrypt.sh

# Configure firewall
echo "Step 8: Configuring firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# Build and start containers (without SSL first)
echo "Step 9: Building Docker images..."
docker-compose build

echo "Step 10: Starting application (HTTP only)..."
docker-compose up -d app

# Wait for app to be ready
echo "Waiting for application to start..."
sleep 10

# Test application
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Application is running!"
else
    echo "✗ Application failed to start. Check logs:"
    echo "  docker-compose logs app"
    exit 1
fi

# Setup SSL
echo ""
echo "Step 11: Setting up SSL certificate..."
echo "Make sure your domain chatwithgithub.pratikpdl.com.np points to this server (194.163.172.56)"
echo "Check DNS: nslookup chatwithgithub.pratikpdl.com.np"
read -p "Press enter when DNS is configured to continue with SSL setup..."

# Update email in init-letsencrypt.sh
read -p "Enter your email for Let's Encrypt notifications: " user_email
sed -i "s/your-email@example.com/$user_email/g" init-letsencrypt.sh

# Run SSL initialization
./init-letsencrypt.sh

# Start all services
echo "Step 12: Starting all services with SSL..."
docker-compose up -d

echo ""
echo "=== Deployment Complete! ==="
echo ""
echo "Your application is running at:"
echo "  https://chatwithgithub.pratikpdl.com.np"
echo ""
echo "Useful commands:"
echo "  - View logs: docker-compose logs -f"
echo "  - View app logs: docker-compose logs -f app"
echo "  - Restart: docker-compose restart"
echo "  - Stop: docker-compose down"
echo "  - Update: docker-compose pull && docker-compose up -d --build"
echo ""
echo "Check status:"
echo "  docker-compose ps"
