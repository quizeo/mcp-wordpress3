#!/bin/bash

# SSL Certificate Generation Script for WordPress MCP Server
# This script generates self-signed SSL certificates for HTTPS testing

echo "🔒 Generating SSL certificates for WordPress MCP Server..."
echo

# Check if OpenSSL is available
if ! command -v openssl &> /dev/null; then
    echo "❌ OpenSSL is not installed. Please install OpenSSL first."
    echo
    echo "Installation instructions:"
    echo "  Windows: Download from https://slproweb.com/products/Win32OpenSSL.html"
    echo "  macOS: brew install openssl"
    echo "  Ubuntu/Debian: sudo apt-get install openssl"
    echo "  CentOS/RHEL: sudo yum install openssl"
    exit 1
fi

# Configuration
DOMAIN="localhost"
CERT_FILE="cert.pem"
KEY_FILE="key.pem"
DAYS=365

echo "📋 Certificate Configuration:"
echo "  Domain: $DOMAIN"
echo "  Certificate file: $CERT_FILE"
echo "  Private key file: $KEY_FILE"
echo "  Validity: $DAYS days"
echo

# Generate private key and certificate
echo "🔑 Generating private key and certificate..."
openssl req -x509 -newkey rsa:4096 \
    -keyout "$KEY_FILE" \
    -out "$CERT_FILE" \
    -days $DAYS \
    -nodes \
    -subj "/C=US/ST=State/L=City/O=WordPress MCP Server/OU=IT Department/CN=$DOMAIN"

if [ $? -eq 0 ]; then
    echo "✅ SSL certificates generated successfully!"
    echo
    echo "📁 Files created:"
    echo "  🔐 Private key: $KEY_FILE"
    echo "  📜 Certificate: $CERT_FILE"
    echo
    echo "🚀 Start HTTPS server with:"
    echo "  uv run python wordpress_mcp_https.py --transport https \\"
    echo "    --ssl-cert $CERT_FILE --ssl-key $KEY_FILE --port 8443"
    echo
    echo "🔗 Claude Desktop URL:"
    echo "  https://localhost:8443/mcp"
    echo
    echo "⚠️  Note: You may need to accept the self-signed certificate"
    echo "   in your browser or Claude Desktop client."
else
    echo "❌ Failed to generate SSL certificates"
    exit 1
fi

# Show certificate information
echo
echo "📋 Certificate Information:"
openssl x509 -in "$CERT_FILE" -text -noout | grep -E "(Subject:|Not Before|Not After|DNS:)"
echo
