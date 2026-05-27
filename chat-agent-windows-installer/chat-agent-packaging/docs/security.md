# Security Best Practices

This guide covers security considerations for deploying and operating Chat-Agent.

## Overview

Chat-Agent handles sensitive data and has access to internal systems. Proper security configuration is critical.

## Pre-Installation Security

### 1. System Hardening

**Linux**:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw enable
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 8000/tcp # Backend (if needed externally)
sudo ufw allow 3000/tcp # Frontend (if needed externally)

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

**Windows**:
```powershell
# Enable Windows Firewall
Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True

# Configure Windows Defender
Set-MpPreference -DisableRealtimeMonitoring $false
```

### 2. User Management

Create dedicated service account with minimal privileges:

```bash
# Linux
sudo useradd -r -s /bin/false chat-agent

# Windows
New-LocalUser -Name "ChatAgent" -NoPassword -UserMayNotChangePassword
```

## Installation Security

### 1. Secure Configuration

Generate strong random keys:

```bash
# Generate SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate ENCRYPTION_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Update `.env`:
```bash
SECRET_KEY=<generated-key>
ENCRYPTION_KEY=<generated-key>
```

### 2. Database Security

**Strong Password**:
```bash
# Generate strong password
openssl rand -base64 32
```

**Configure PostgreSQL**:
```bash
# Edit pg_hba.conf
# Change: host all all 0.0.0.0/0 md5
# To:     host chatbot chatbot_user 127.0.0.1/32 md5

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### 3. File Permissions

**Linux**:
```bash
# Restrict config file
chmod 600 /etc/chat-agent/.env
chown chat-agent:chat-agent /etc/chat-agent/.env

# Restrict application directory
chmod 750 /opt/chat-agent
chown -R chat-agent:chat-agent /opt/chat-agent
```

**Windows**:
```powershell
# Restrict config file
$acl = Get-Acl "$env:ProgramData\ChatAgent\.env"
$acl.SetAccessRuleProtection($true, $false)
$rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    "ChatAgent", "Read", "Allow"
)
$acl.AddAccessRule($rule)
Set-Acl "$env:ProgramData\ChatAgent\.env" $acl
```

## Network Security

### 1. Firewall Configuration

Only expose necessary ports:

```bash
# Internal deployment (recommended)
# Only allow localhost access
# Backend: 127.0.0.1:8000
# Frontend: 127.0.0.1:3000

# External deployment (if needed)
# Use reverse proxy (nginx/apache)
# Enable HTTPS
# Restrict source IPs
```

### 2. TLS/SSL

**Use reverse proxy with HTTPS**:

```nginx
# nginx configuration
server {
    listen 443 ssl http2;
    server_name chat-agent.example.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. VPN Requirement

For internal tools, require VPN:

```bash
# Check if VPN is connected before allowing access
# Add to service startup script

if ! ip addr show tun0 &> /dev/null; then
    echo "VPN not connected. Exiting."
    exit 1
fi
```

## Application Security

### 1. Environment Variables

Never hardcode secrets:

```python
# ✗ BAD
API_KEY = "sk-1234567890"

# ✓ GOOD
import os
API_KEY = os.getenv("API_KEY")
```

### 2. Input Validation

All user input is validated:

```python
# Already implemented in application
# But verify configuration:
DEBUG=false  # Never enable in production
```

### 3. API Key Management

Store API keys securely:

```bash
# Use environment variables
ANTHROPIC_API_KEY=sk-...
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Or use secrets management
# AWS Secrets Manager
# HashiCorp Vault
# Azure Key Vault
```

## Tool Security

### 1. Tool Permissions

Follow principle of least privilege:

```bash
# Minimal configuration
ENABLED_TOOLS=public_web_search

# Add tools as needed
ENABLED_TOOLS=public_web_search,internal_search
```

### 2. Tool Authentication

Each tool requires proper authentication:

```bash
# Internal Search
CONFLUENCE_TOKEN=...
JIRA_TOKEN=...

# Netra
NETRA_API_KEY=...

# DISH Tools
DISH_TOOLS_TOKEN=...

# Kubernetes
KUBECONFIG=/path/to/config
```

### 3. Audit Logging

Enable audit logging for all tools:

```bash
# In .env
AUDIT_LOGGING=true
AUDIT_LOG_FILE=/var/log/chat-agent/audit.log
```

Review logs regularly:

```bash
# Check for suspicious activity
grep "SECURITY" /var/log/chat-agent/audit.log

# Check failed authentication
grep "AUTH_FAILED" /var/log/chat-agent/audit.log
```

## Operational Security

### 1. Regular Updates

Keep system updated:

```bash
# Linux
sudo apt update && sudo apt upgrade -y

# Python dependencies
cd /opt/chat-agent/backend
sudo -u chat-agent venv/bin/pip install --upgrade -r requirements.txt

# Node dependencies
cd /opt/chat-agent/frontend
sudo -u chat-agent pnpm update
```

### 2. Backup Security

Encrypt backups:

```bash
# Encrypt backup
tar -czf - /opt/chat-agent | gpg --encrypt -r admin@example.com > backup.tar.gz.gpg

# Decrypt backup
gpg --decrypt backup.tar.gz.gpg | tar -xzf -
```

Store backups securely:
- Encrypted storage
- Off-site location
- Access control
- Regular testing

### 3. Monitoring

Monitor for security events:

```bash
# Failed login attempts
grep "Failed" /var/log/auth.log

# Application errors
grep "ERROR" /var/log/chat-agent/backend.log

# Suspicious tool usage
grep "SECURITY" /var/log/chat-agent/audit.log
```

Set up alerts:

```bash
# Example: Alert on failed auth
tail -f /var/log/auth.log | grep --line-buffered "Failed" | while read line; do
    echo "$line" | mail -s "Security Alert" admin@example.com
done
```

## Incident Response

### 1. Suspected Breach

If you suspect a security breach:

1. **Isolate**: Stop services immediately
```bash
sudo systemctl stop chat-agent-backend chat-agent-frontend
```

2. **Preserve**: Don't delete logs
```bash
# Copy logs to secure location
sudo cp -r /var/log/chat-agent /secure/location/logs-$(date +%Y%m%d)
```

3. **Investigate**: Review logs
```bash
# Check access logs
grep "ERROR\|WARN\|SECURITY" /var/log/chat-agent/*.log

# Check system logs
sudo journalctl -u chat-agent-backend --since "1 hour ago"
```

4. **Notify**: Contact security team

5. **Remediate**: Fix vulnerability

6. **Rotate**: Change all credentials
```bash
# Generate new keys
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env
# Restart services
```

### 2. Credential Rotation

Rotate credentials regularly:

```bash
# Database password
ALTER USER chatbot_user WITH PASSWORD 'new_password';

# Update .env
POSTGRES_PASSWORD=new_password

# Restart services
sudo systemctl restart chat-agent-backend
```

## Compliance

### 1. Data Protection

- Encrypt data at rest
- Encrypt data in transit
- Implement access controls
- Log all access
- Regular audits

### 2. Data Retention

Configure retention policies:

```bash
# Rotate logs
# /etc/logrotate.d/chat-agent
/var/log/chat-agent/*.log {
    daily
    rotate 90
    compress
    delaycompress
    notifempty
    create 640 chat-agent chat-agent
}
```

### 3. Access Control

Implement role-based access:

```bash
# Developer
ENABLED_TOOLS=public_web_search,internal_search

# Support
ENABLED_TOOLS=public_web_search,dish_internal_tool

# Admin
ENABLED_TOOLS=public_web_search,internal_search,netra_search,dish_internal_tool,cluster_inspect
```

## Security Checklist

- [ ] System hardened and updated
- [ ] Strong passwords and keys generated
- [ ] File permissions configured
- [ ] Firewall configured
- [ ] TLS/SSL enabled
- [ ] VPN required for internal access
- [ ] API keys stored securely
- [ ] Audit logging enabled
- [ ] Backup encryption enabled
- [ ] Monitoring configured
- [ ] Incident response plan documented
- [ ] Regular security reviews scheduled

## Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## Support

For security concerns:

1. Contact security team immediately
2. Do not attempt to fix security issues yourself
3. Preserve all logs and evidence
4. Follow incident response procedures

---

**Last Updated**: 2026-02-04  
**Version**: 1.0.0  
**Classification**: Internal Use Only
