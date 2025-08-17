# 🚀 Ready to Deploy Your WordPress Sites to Render!

## 📊 **Your Configuration Summary:**

### **WordPress Sites Configured:**

1. **GenerateBetter AI Site**

   - URL: https://generatebetter.ai
   - Username: admin
   - ✅ App password configured

2. **Only Winners In The Building**
   - URL: https://onlywinnersinthebuilding.com
   - Username: buxx14@gmail.com
   - ✅ App password configured

## 🎯 **Two Deployment Options:**

### **Option 1: Deploy with Config File (Simpler)**

Your current `mcp-wordpress.config.json` already contains both sites and will work directly on Render.

**Steps:**

1. Push your code to GitHub
2. Create Render Web Service
3. Deploy - credentials are already in the config file
4. Get your URL: `https://your-service-name.onrender.com/mcp`

### **Option 2: Use Environment Variables (More Secure)**

Move credentials to Render environment variables for better security.

**Render Environment Variables to Set:**

```
MCP_API_KEY=your-secure-api-key-here

# GenerateBetter AI Site
WORDPRESS_SITE_URL_1=https://generatebetter.ai
WORDPRESS_USERNAME_1=admin
WORDPRESS_APP_PASSWORD_1=6H9J H0ah RvRa pqQG Uy45 Qndx
WORDPRESS_AUTH_METHOD_1=app-password
WORDPRESS_SITE_NAME_1=GenerateBetter AI Site

# Only Winners In The Building
WORDPRESS_SITE_URL_2=https://onlywinnersinthebuilding.com
WORDPRESS_USERNAME_2=buxx14@gmail.com
WORDPRESS_APP_PASSWORD_2=kYXT OH6j Srr0 g4Yb kcub exdy
WORDPRESS_AUTH_METHOD_2=app-password
WORDPRESS_SITE_NAME_2=Only Winners In The Building
```

## 🔑 **Generate Your API Key:**

Run this command to generate a secure API key:

```bash
python -c "import secrets, base64; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
```

## 🚀 **Quick Deploy Commands:**

```bash
# 1. Commit your changes
git add .
git commit -m "WordPress MCP Server with GenerateBetter and OnlyWinners sites"

# 2. Push to GitHub
git push origin main

# 3. Deploy on Render (via dashboard)
# Your service will be available at: https://your-service-name.onrender.com/mcp
```

## 🔌 **Claude Desktop Setup:**

Once deployed, configure Claude Desktop:

```
Name: WordPress MCP (GenerateBetter + OnlyWinners)
URL: https://your-service-name.onrender.com/mcp
Headers: Authorization: Bearer your-generated-api-key
```

## ✅ **What You'll Get:**

- **Remote WordPress management** for both sites through Claude Desktop
- **All 59 WordPress tools** available for both sites
- **Site switching** with `site` parameter: `generatebetter-ai` or `onlywinnersinthebuilding`
- **Secure cloud hosting** on Render with HTTPS
- **Auto-deployment** on code changes

## 🎯 **Example Usage in Claude Desktop:**

```
# Work with GenerateBetter AI site
"Get posts from GenerateBetter site"
→ Uses wp_list_posts with site='generatebetter-ai'

# Work with OnlyWinners site
"Create a post on OnlyWinners site"
→ Uses wp_create_post with site='onlywinnersinthebuilding'

# Get status of both sites
"Check WordPress authentication status"
→ Will prompt for site selection or show both
```

🎉 **Your WordPress MCP Server is ready to deploy with both sites configured!**
