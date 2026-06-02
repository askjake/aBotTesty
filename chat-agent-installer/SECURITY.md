# Security Configuration Guide

## 🔐 Required Environment Variables

When deploying the chat agent installer, you **must** set these environment variables with your actual credentials:

### Backend (.env.production)
```bash
# Sentry Configuration
SENTRY_AUTH_TOKEN=your_sentry_auth_token_here
SENTRY_ORG=dishtv.technology
SENTRY_URL=https://ds-testing-sentry

# Production Settings
LOCAL=false
DEBUG=false

# LangGraph Configuration
LANGGRAPH_RECURSION_LIMIT=200
```

### SSH Transfer (if using transfer script)
The transfer_bundle.sh script is **not included** in this repository for security reasons.
If you need to transfer files via SSH, create a local script with:
```bash
SSH_HOST=your_server_hostname
SSH_USER=your_username
SSH_PASSWORD=your_password  # Or use SSH keys instead
```

## 🚨 Security Best Practices

1. **Never commit credentials to git**
   - Use environment variables
   - Use secret management tools (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Keep .env.local files in .gitignore

2. **Rotate credentials regularly**
   - GitHub tokens should have expiration dates
   - Sentry tokens should be rotated quarterly
   - SSH passwords should be replaced with key-based auth

3. **Use minimal permissions**
   - GitHub tokens: only grant necessary repo permissions
   - Sentry tokens: scope to specific projects
   - SSH users: use dedicated deployment accounts with limited access

4. **Monitor for exposed secrets**
   - GitHub has secret scanning enabled
   - Use tools like gitleaks or truffleHog
   - Set up alerts for credential exposure

## 📋 Deployment Checklist

- [ ] Clone this repository
- [ ] Create .env.local files with actual credentials
- [ ] Verify .env.local is in .gitignore
- [ ] Test the installation locally
- [ ] Deploy to target environment
- [ ] Verify all services are running
- [ ] Delete any local credential files after deployment
- [ ] Rotate any credentials that were temporarily stored

## 🔍 Files That Were Sanitized

The following files had credentials removed before pushing to GitHub:

1. **app/backend/.env.production**
   - Removed: SENTRY_AUTH_TOKEN value
   - Now: Empty placeholder for environment variable

2. **app/frontend/apps/chats/.env.production**
   - Status: Contains only public URLs (safe)

3. **scripts/transfer_bundle.sh**
   - Status: NOT included in repository (contained SSH credentials)

## 📞 Support

If you need access to the original credentials:
- Contact: montjac@dish.com
- Sentry access: Request from DevOps team
- SSH access: Request from Infrastructure team
