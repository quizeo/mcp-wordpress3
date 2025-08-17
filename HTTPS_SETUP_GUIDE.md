# WordPress MCP Server - HTTPS Setup Guide

## 🎯 Overview

This guide shows how to run the WordPress MCP Server with HTTPS transport for integration with Claude Desktop's "Add custom connector" feature.

## 📋 Prerequisites

- Python 3.8+ with uv package manager
- WordPress site(s) with application passwords configured
- (Optional) SSL certificates for HTTPS

## 🚀 Quick Start

### 1. Basic HTTP Setup (Recommended for Testing)

```bash
# Start the server with HTTP transport
uv run python wordpress_mcp_https.py --transport http --port 8000

# Or with custom settings
uv run python wordpress_mcp_https.py --transport http --host 0.0.0.0 --port 8080
```

### 2. HTTPS Setup (Production Ready)

```bash
# Generate self-signed certificate for testing
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Start HTTPS server
uv run python wordpress_mcp_https.py --transport https --port 8443 \
  --ssl-cert cert.pem --ssl-key key.pem
```

### 3. Stdio Mode (Original)

```bash
# Traditional stdio mode for local development
uv run python wordpress_mcp_https.py --transport stdio
```

## ⚙️ Configuration

### WordPress Sites Configuration

Edit `mcp-wordpress.config.json`:

```json
{
  "sites": [
    {
      "id": "my-site",
      "name": "My WordPress Site",
      "config": {
        "WORDPRESS_SITE_URL": "https://example.com",
        "WORDPRESS_USERNAME": "admin",
        "WORDPRESS_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx",
        "WORDPRESS_AUTH_METHOD": "app-password"
      }
    }
  ],
  "server": {
    "host": "localhost",
    "port": 8000,
    "ssl_cert_path": null,
    "ssl_key_path": null,
    "api_key": null,
    "cors_origins": ["*"],
    "mount_path": "/mcp"
  }
}
```

### Server Configuration Options

| Option          | Description               | Default        |
| --------------- | ------------------------- | -------------- |
| `host`          | Server host address       | `localhost`    |
| `port`          | Server port               | `8000`         |
| `ssl_cert_path` | SSL certificate file path | `null`         |
| `ssl_key_path`  | SSL private key file path | `null`         |
| `api_key`       | Authentication API key    | Auto-generated |
| `cors_origins`  | Allowed CORS origins      | `["*"]`        |
| `mount_path`    | MCP endpoint path         | `/mcp`         |

## 🔌 Claude Desktop Integration

### Step 1: Start the Server

```bash
uv run python wordpress_mcp_https.py --transport http --port 8000
```

You'll see output like:

```
================================================================================
🚀 WordPress MCP Server (HTTPS) Started!
================================================================================
🌐 Protocol: HTTP
🏠 Host: localhost
🔌 Port: 8000
📍 MCP Endpoint: http://localhost:8000/mcp
🔑 API Key: KgQZ4xpbIZK5jMM4wSe9dTCbNGQSg082jvBmPXwt_Dc=
```

### Step 2: Configure Claude Desktop

1. **Open Claude Desktop**
2. **Go to Settings** → **Custom Connectors**
3. **Add New Connector:**
   - **Name:** WordPress MCP Server
   - **URL:** `http://localhost:8000/mcp`
   - **Headers:** (Optional but recommended)
     ```
     Authorization: Bearer KgQZ4xpbIZK5jMM4wSe9dTCbNGQSg082jvBmPXwt_Dc=
     ```

### Step 3: Test the Connection

Claude Desktop should now be able to connect and use all 59 WordPress tools!

## 🔒 Security Configuration

### API Key Authentication

The server automatically generates a secure API key. You can:

1. **Use the auto-generated key** (shown in server output)
2. **Provide your own key:**
   ```bash
   uv run python wordpress_mcp_https.py --transport http \
     --api-key "your-custom-api-key-here"
   ```
3. **Set in configuration file:**
   ```json
   {
     "server": {
       "api_key": "your-api-key-here"
     }
   }
   ```

### CORS Configuration

For production, restrict CORS origins:

```json
{
  "server": {
    "cors_origins": ["https://claude.ai", "https://app.claude.ai"]
  }
}
```

### HTTPS for Production

1. **Obtain SSL certificates** (Let's Encrypt, CA, or self-signed)
2. **Configure HTTPS:**
   ```bash
   uv run python wordpress_mcp_https.py --transport https \
     --ssl-cert /path/to/cert.pem \
     --ssl-key /path/to/key.pem \
     --host 0.0.0.0 --port 443
   ```

## 🛠️ Command Line Options

```bash
usage: wordpress_mcp_https.py [-h] [--transport {stdio,http,https}]
                              [--host HOST] [--port PORT]
                              [--ssl-cert SSL_CERT] [--ssl-key SSL_KEY]
                              [--api-key API_KEY] [--mount-path MOUNT_PATH]

WordPress MCP Server with HTTPS support

options:
  -h, --help            show this help message and exit
  --transport {stdio,http,https}
                        Transport method (default: stdio)
  --host HOST           Host to bind to (default: localhost)
  --port PORT           Port to bind to (default: 8000)
  --ssl-cert SSL_CERT   Path to SSL certificate file (required for HTTPS)
  --ssl-key SSL_KEY     Path to SSL private key file (required for HTTPS)
  --api-key API_KEY     API key for authentication (auto-generated if not provided)
  --mount-path MOUNT_PATH
                        Mount path for MCP endpoint (default: /mcp)
```

## 🧪 Testing the Server

### 1. Health Check

```bash
curl -X GET http://localhost:8000/mcp \
  -H "Accept: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 2. List Available Tools

Use the MCP client to list tools:

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def test_connection():
    async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Available tools: {len(tools.tools)}")

asyncio.run(test_connection())
```

## 🔧 Troubleshooting

### Common Issues

1. **Port already in use:**

   ```bash
   # Use a different port
   uv run python wordpress_mcp_https.py --transport http --port 8001
   ```

2. **SSL certificate issues:**

   ```bash
   # Generate new self-signed certificate
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
   ```

3. **Claude Desktop connection fails:**

   - Check the server is running and accessible
   - Verify the URL in Claude Desktop matches the server output
   - Ensure API key is correctly configured (if using authentication)

4. **WordPress authentication errors:**
   - Verify application passwords are configured in WordPress
   - Check username and password in configuration file
   - Test with `wp_test_auth` tool

### Debug Mode

Enable debug logging:

```bash
export LOGGING_LEVEL=DEBUG
uv run python wordpress_mcp_https.py --transport http
```

## 🌐 Production Deployment

### Docker Deployment

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install uv
RUN uv sync

EXPOSE 8000

CMD ["uv", "run", "python", "wordpress_mcp_https.py", "--transport", "http", "--host", "0.0.0.0", "--port", "8000"]
```

### Cloud Deployment

1. **Deploy to cloud provider** (AWS, GCP, Azure, etc.)
2. **Configure load balancer** for HTTPS termination
3. **Set environment variables** for configuration
4. **Use proper SSL certificates**

### Reverse Proxy (Nginx)

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /mcp {
        proxy_pass http://localhost:8000/mcp;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## ✅ Verification Checklist

- [ ] Server starts without errors
- [ ] Configuration file loads properly
- [ ] All 59 WordPress tools are registered
- [ ] HTTP/HTTPS endpoint is accessible
- [ ] Claude Desktop can connect successfully
- [ ] WordPress authentication works
- [ ] API key authentication (if enabled) works
- [ ] SSL certificates are valid (for HTTPS)

## 📚 Additional Resources

- [MCP Python SDK Documentation](https://github.com/modelcontextprotocol/python-sdk)
- [WordPress REST API Documentation](https://developer.wordpress.org/rest-api/)
- [Claude Desktop Documentation](https://claude.ai/download)
- [OpenSSL Certificate Generation](https://www.openssl.org/docs/)

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review server logs for error messages
3. Verify WordPress site configuration
4. Test with simple HTTP transport first before HTTPS
