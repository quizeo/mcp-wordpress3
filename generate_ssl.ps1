# SSL Certificate Generation Script for WordPress MCP Server (PowerShell)
# This script generates self-signed SSL certificates for HTTPS testing on Windows

Write-Host "🔒 Generating SSL certificates for WordPress MCP Server..." -ForegroundColor Green
Write-Host ""

# Configuration
$Domain = "localhost"
$CertFile = "cert.pem"
$KeyFile = "key.pem"
$Days = 365

Write-Host "📋 Certificate Configuration:" -ForegroundColor Blue
Write-Host "  Domain: $Domain"
Write-Host "  Certificate file: $CertFile"
Write-Host "  Private key file: $KeyFile"
Write-Host "  Validity: $Days days"
Write-Host ""

# Check if OpenSSL is available
$OpenSSLPath = Get-Command openssl -ErrorAction SilentlyContinue

if (-not $OpenSSLPath) {
    Write-Host "❌ OpenSSL is not installed or not in PATH." -ForegroundColor Red
    Write-Host ""
    Write-Host "Installation options:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://slproweb.com/products/Win32OpenSSL.html"
    Write-Host "  2. Install with Chocolatey: choco install openssl"
    Write-Host "  3. Install with Scoop: scoop install openssl"
    Write-Host "  4. Use Windows Subsystem for Linux (WSL)"
    Write-Host ""
    Write-Host "Alternative: Use PowerShell native certificate generation (less compatible):"
    Write-Host "  New-SelfSignedCertificate -DnsName 'localhost' -CertStoreLocation 'Cert:\LocalMachine\My'"
    exit 1
}

# Generate private key and certificate
Write-Host "🔑 Generating private key and certificate..." -ForegroundColor Green

$OpenSSLArgs = @(
    "req", "-x509", "-newkey", "rsa:4096",
    "-keyout", $KeyFile,
    "-out", $CertFile,
    "-days", $Days,
    "-nodes",
    "-subj", "/C=US/ST=State/L=City/O=WordPress MCP Server/OU=IT Department/CN=$Domain"
)

try {
    & openssl $OpenSSLArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ SSL certificates generated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📁 Files created:" -ForegroundColor Blue
        Write-Host "  🔐 Private key: $KeyFile"
        Write-Host "  📜 Certificate: $CertFile"
        Write-Host ""
        Write-Host "🚀 Start HTTPS server with:" -ForegroundColor Yellow
        Write-Host "  uv run python wordpress_mcp_https.py --transport https \"
        Write-Host "    --ssl-cert $CertFile --ssl-key $KeyFile --port 8443"
        Write-Host ""
        Write-Host "🔗 Claude Desktop URL:" -ForegroundColor Cyan
        Write-Host "  https://localhost:8443/mcp"
        Write-Host ""
        Write-Host "⚠️  Note: You may need to accept the self-signed certificate" -ForegroundColor Yellow
        Write-Host "   in your browser or Claude Desktop client."
        
        # Show certificate information
        Write-Host ""
        Write-Host "📋 Certificate Information:" -ForegroundColor Blue
        & openssl x509 -in $CertFile -text -noout | Select-String -Pattern "(Subject:|Not Before|Not After|DNS:)"
        
    } else {
        Write-Host "❌ Failed to generate SSL certificates" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error generating certificates: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 Certificate generation complete!" -ForegroundColor Green
