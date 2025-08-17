#!/bin/bash

# WordPress MCP Server - Render Deployment Helper Script
# This script helps prepare your project for Render deployment

echo "🚀 WordPress MCP Server - Render Deployment Helper"
echo "=================================================="

# Function to generate API key
generate_api_key() {
    python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
}

# Check if git repository exists
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    echo "✅ Git repository initialized"
else
    echo "✅ Git repository found"
fi

# Generate API key
echo ""
echo "🔑 Generating secure API key..."
API_KEY=$(generate_api_key)
echo "Generated API key: $API_KEY"
echo "💡 Copy this key to use in Render environment variables"

# Check for WordPress configuration
echo ""
echo "🔍 Checking WordPress configuration..."
if [ -f "mcp-wordpress.config.json" ]; then
    SITE_COUNT=$(python -c "import json; config=json.load(open('mcp-wordpress.config.json')); print(len(config.get('sites', [])))")
    echo "✅ Found $SITE_COUNT WordPress sites in config file"
else
    echo "⚠️  No mcp-wordpress.config.json found"
fi

# Run validation
echo ""
echo "🧪 Running deployment validation..."
python validate_render_deployment.py

# Git status
echo ""
echo "📊 Git Status:"
git status --porcelain

# Instructions
echo ""
echo "🚀 Next Steps for Render Deployment:"
echo "1. Add and commit your files:"
echo "   git add ."
echo "   git commit -m 'WordPress MCP Server ready for Render'"
echo ""
echo "2. Push to GitHub:"
echo "   git remote add origin https://github.com/yourusername/your-repo.git"
echo "   git push -u origin main"
echo ""
echo "3. Deploy on Render:"
echo "   - Go to https://dashboard.render.com"
echo "   - Create new Web Service"
echo "   - Connect your GitHub repository"
echo "   - Set environment variables (including API key above)"
echo ""
echo "4. Claude Desktop URL will be:"
echo "   https://your-service-name.onrender.com/mcp"
echo ""
echo "📖 See RENDER_DEPLOYMENT_GUIDE.md for detailed instructions"
