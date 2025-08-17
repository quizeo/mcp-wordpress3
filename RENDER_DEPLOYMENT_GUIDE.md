# WordPress MCP Server - Render Deployment Guide

## 🚀 Deploy to Render

This guide shows how to deploy the WordPress MCP HTTPS server to Render for production use with Claude Desktop.

## 📋 Prerequisites

- Render account (free tier available)
- GitHub repository with your WordPress MCP server code
- WordPress site(s) with application passwords configured

## 🔧 Deployment Methods

### Method 1: GitHub Integration (Recommended)

#### Step 1: Prepare Your Repository

1. **Push your code to GitHub:**

   ```bash
   git add .
   git commit -m "WordPress MCP Server ready for Render deployment"
   git push origin main
   ```

2. **Ensure these files are in your repository:**
   - `Dockerfile` ✅
   - `render.yaml` ✅
   - `wordpress_mcp_https.py` ✅
   - `mcp-wordpress.config.json` ✅
   - `pyproject.toml` ✅

#### Step 2: Deploy on Render

1. **Go to [Render Dashboard](https://dashboard.render.com)**

2. **Create New Web Service:**

   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Select your WordPress MCP repository

3. **Configure the service:**

   ```
   Name: wordpress-mcp-server
   Environment: Docker
   Plan: Starter (Free) or paid plan
   Auto-Deploy: Yes
   ```

4. **Set Environment Variables:**

   ```
   MCP_API_KEY=your-secure-api-key-here
   WORDPRESS_SITE_URL_1=https://your-wordpress-site.com
   WORDPRESS_USERNAME_1=your-username
   WORDPRESS_APP_PASSWORD_1=your-app-password
   ```

5. **Deploy:**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app

#### Step 3: Configure Health Check

Render will automatically use the health check path defined in `render.yaml`:

```yaml
healthCheckPath: /mcp
```

### Method 2: Manual Docker Deployment

#### Step 1: Build and Test Locally

```bash
# Build Docker image
docker build -t wordpress-mcp-server .

# Test locally
docker run -p 10000:10000 \
  -e MCP_API_KEY="your-api-key" \
  wordpress-mcp-server
```

#### Step 2: Deploy to Render

1. **Create new Web Service**
2. **Choose "Deploy an existing image"**
3. **Push your image to Docker Hub or use Render's build service**

## ⚙️ Configuration

### Environment Variables

Set these in your Render service environment:

| Variable      | Description                      | Example               |
| ------------- | -------------------------------- | --------------------- |
| `MCP_API_KEY` | API key for authentication       | `your-secure-key-123` |
| `PORT`        | Server port (auto-set by Render) | `10000`               |
| `HOST`        | Server host (should be 0.0.0.0)  | `0.0.0.0`             |

### WordPress Sites Configuration

You can configure WordPress sites in two ways:

#### Option 1: Environment Variables (Secure)

```bash
WORDPRESS_SITE_URL_1=https://site1.com
WORDPRESS_USERNAME_1=admin
WORDPRESS_APP_PASSWORD_1=xxxx xxxx xxxx xxxx
WORDPRESS_AUTH_METHOD_1=app-password

WORDPRESS_SITE_URL_2=https://site2.com
WORDPRESS_USERNAME_2=admin
WORDPRESS_APP_PASSWORD_2=yyyy yyyy yyyy yyyy
WORDPRESS_AUTH_METHOD_2=app-password
```

#### Option 2: Configuration File (Less secure)

Update `mcp-wordpress.config.json` with your sites (passwords will be visible in code).

## 🔗 Claude Desktop Integration

### Step 1: Get Your Render URL

After deployment, your server will be available at:

```
https://wordpress-mcp-server.onrender.com/mcp
```

### Step 2: Configure Claude Desktop

1. **Open Claude Desktop**
2. **Go to Settings → Custom Connectors**
3. **Add New Connector:**
   ```
   Name: WordPress MCP Server (Render)
   URL: https://your-service-name.onrender.com/mcp
   Headers: Authorization: Bearer your-api-key-here
   ```

### Step 3: Test Connection

Claude Desktop should now connect to your Render-deployed WordPress MCP server and have access to all 59 WordPress tools!

## 🔒 Security Best Practices

### API Key Security

1. **Generate a strong API key:**

   ```bash
   python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   ```

2. **Set in Render environment variables** (not in code)

3. **Use HTTPS only** (Render provides this automatically)

### WordPress Credentials

1. **Use application passwords** (not main passwords)
2. **Store in environment variables** on Render
3. **Limit WordPress user permissions** to only what's needed

### CORS Configuration

For production, restrict CORS origins in your config:

```json
{
  "server": {
    "cors_origins": ["https://claude.ai", "https://app.claude.ai"]
  }
}
```

## 📊 Monitoring and Logs

### Render Dashboard

- **View logs**: Render Dashboard → Your Service → Logs
- **Monitor performance**: Check CPU, memory, and response times
- **Scale if needed**: Upgrade to paid plans for more resources

### Health Checks

Render automatically monitors your service health via the `/mcp` endpoint. Your service will be restarted if health checks fail.

## 🔧 Troubleshooting

### Common Issues

1. **Build Failures:**

   ```bash
   # Check Dockerfile syntax
   docker build -t test .

   # Verify dependencies
   uv sync --frozen
   ```

2. **Service Won't Start:**

   - Check environment variables are set correctly
   - Verify port 10000 is exposed and bound to 0.0.0.0
   - Check application logs in Render dashboard

3. **Claude Desktop Connection Issues:**

   - Verify the URL includes `/mcp` path
   - Check API key is correctly set in headers
   - Ensure service is running and healthy

4. **WordPress Connection Errors:**
   - Verify WordPress application passwords are valid
   - Check WordPress site URLs are accessible
   - Test credentials manually with WordPress REST API

### Debug Mode

Enable debug logging by setting environment variable:

```
LOGGING_LEVEL=DEBUG
```

## 💰 Pricing

### Render Free Tier

- ✅ Perfect for testing and small projects
- ✅ 750 hours/month of runtime
- ⚠️ Services sleep after 15 minutes of inactivity
- ⚠️ Cold start delays (30-60 seconds)

### Render Paid Plans

- ✅ Always-on services (no sleeping)
- ✅ Faster performance
- ✅ More memory and CPU
- ✅ Custom domains

## 🚀 Advanced Configuration

### Custom Domain

1. **Upgrade to paid plan**
2. **Add custom domain** in Render dashboard
3. **Update Claude Desktop URL** to use your domain:
   ```
   https://yourdomain.com/mcp
   ```

### Scaling

For high traffic:

1. **Upgrade Render plan** for more resources
2. **Consider multiple instances** with load balancing
3. **Implement caching** for WordPress API responses

### Monitoring

Set up monitoring with external services:

- **Uptime monitoring**: UptimeRobot, Pingdom
- **Error tracking**: Sentry, Rollbar
- **Performance monitoring**: New Relic, DataDog

## 📚 Example Deployment

Here's a complete example configuration:

### Render Environment Variables:

```
MCP_API_KEY=KgQZ4xpbIZK5jMM4wSe9dTCbNGQSg082jvBmPXwt_Dc=
WORDPRESS_SITE_URL_1=https://mysite.com
WORDPRESS_USERNAME_1=admin
WORDPRESS_APP_PASSWORD_1=abcd efgh ijkl mnop qrst uvwx
```

### Claude Desktop Configuration:

```
Name: My WordPress MCP
URL: https://wordpress-mcp-server-xyz.onrender.com/mcp
Headers: Authorization: Bearer KgQZ4xpbIZK5jMM4wSe9dTCbNGQSg082jvBmPXwt_Dc=
```

## ✅ Deployment Checklist

- [ ] Code pushed to GitHub repository
- [ ] Dockerfile and render.yaml in repository
- [ ] Render service created and configured
- [ ] Environment variables set (API key, WordPress credentials)
- [ ] Service successfully deployed and running
- [ ] Health check passing (`/mcp` endpoint responding)
- [ ] Claude Desktop connector configured
- [ ] WordPress tools accessible through Claude Desktop
- [ ] Monitoring and alerting set up (optional)

🎉 **Your WordPress MCP server is now deployed on Render and ready for production use with Claude Desktop!**
