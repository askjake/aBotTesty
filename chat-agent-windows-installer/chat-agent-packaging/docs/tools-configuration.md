# Tool Configuration Guide

This guide explains how to configure and use each tool available in Chat-Agent.

## Overview

Chat-Agent supports multiple tools that can be enabled or disabled based on your needs. Each tool has specific requirements and permissions.

## Available Tools

### 1. public_web_search

**Purpose**: Search public internet for current information

**Use Cases**:
- Weather information
- News and current events
- Stock prices
- General knowledge queries
- Public documentation

**Requirements**:
- Internet access
- No authentication required

**Configuration**:
```bash
# Enable in .env
ENABLED_TOOLS=public_web_search,...
```

**Security Notes**:
- Never include proprietary information in search queries
- All searches are logged
- Queries are sent to external services

---

### 2. internal_search

**Purpose**: Search DISH internal systems (Confluence, JIRA, Git)

**Use Cases**:
- Find internal documentation
- Search JIRA tickets
- Search code repositories
- Find team information

**Requirements**:
- VPN or internal network access
- Authentication credentials
- Permissions to access internal systems

**Configuration**:
```bash
# Enable in .env
ENABLED_TOOLS=internal_search,...

# Configure access
CONFLUENCE_URL=https://confluence.internal
JIRA_URL=https://jira.internal
GIT_URL=https://git.internal

# Authentication
INTERNAL_SEARCH_TOKEN=your_token
```

**Security Notes**:
- Requires authentication
- Respects user permissions
- Audit logged

---

### 3. netra_search

**Purpose**: Search Netra logs and records

**Use Cases**:
- Search system logs
- Find specific record IDs
- Investigate issues
- Operational data lookup

**Requirements**:
- Netra system access
- Valid credentials
- Network access to Netra

**Configuration**:
```bash
# Enable in .env
ENABLED_TOOLS=netra_search,...

# Configure Netra access
NETRA_URL=https://netra.internal
NETRA_API_KEY=your_key
```

**Usage Example**:
```python
# Search by record ID
netra_search(rec_id="1971450629", search_date="20260204")

# General search
netra_search(query="error logs", search_date="20260204")
```

**Security Notes**:
- Internal only
- Requires API key
- Access logged

---

### 4. dish_internal_tool

**Purpose**: Access DISH internal tools (CART, CCTools, Portal)

**Use Cases**:
- Customer account lookup (CART)
- Support tools (CCTools)
- Internal portal access

**Requirements**:
- DISH internal network
- Tool-specific credentials
- Proper authorization

**Configuration**:
```bash
# Enable in .env
ENABLED_TOOLS=dish_internal_tool,...

# Configure access
CART_URL=https://cart.internal
CCTOOLS_URL=https://cctools.internal
PORTAL_URL=https://portal.internal

# Authentication
DISH_TOOLS_TOKEN=your_token
```

**Available Services**:
- `cart`: Customer Account Research Tool
- `cctools`: Customer Care Tools
- `portal`: Internal Tools Portal

**Usage Example**:
```python
# CART lookup
dish_internal_tool(
    service="cart",
    endpoint="/api/search",
    params={"account": "12345"}
)

# CCTools lookup
dish_internal_tool(
    service="cctools",
    endpoint="/api/lookup",
    params={"phone": "555-1234"}
)
```

**Security Notes**:
- Highly sensitive
- Requires multi-factor authentication
- All access audited
- Customer data protection applies

---

### 5. cluster_inspect

**Purpose**: Kubernetes cluster inspection (read-only)

**Use Cases**:
- List pods and services
- Check deployment status
- View logs
- Inspect cluster resources

**Requirements**:
- kubectl access
- Cluster credentials
- Proper RBAC permissions

**Configuration**:
```bash
# Enable in .env
ENABLED_TOOLS=cluster_inspect,...

# Configure kubectl
KUBECONFIG=/path/to/kubeconfig

# Or use in-cluster config
USE_IN_CLUSTER_CONFIG=true
```

**Available Commands**:
- `list sentry claims`
- `list sentry pods`
- `list all pods`
- `list namespaces`
- `list nodes`
- `describe pod <name> in <namespace>`
- `logs from <pod> in <namespace>`

**Usage Example**:
```python
# List pods
cluster_inspect(task="list sentry pods")

# Get logs
cluster_inspect(task="logs from my-pod in default")
```

**Security Notes**:
- Read-only operations only
- No write/delete permissions
- Respects RBAC
- All commands logged

---

## Configuring Multiple Tools

You can enable multiple tools at once:

```bash
ENABLED_TOOLS=public_web_search,internal_search,netra_search
```

## Permission Management

### Principle of Least Privilege

Only enable tools that are needed for your use case:

```bash
# For general use
ENABLED_TOOLS=public_web_search

# For internal development
ENABLED_TOOLS=public_web_search,internal_search,cluster_inspect

# For operations/support
ENABLED_TOOLS=public_web_search,netra_search,dish_internal_tool

# For full access
ENABLED_TOOLS=public_web_search,internal_search,netra_search,dish_internal_tool,cluster_inspect
```

### Role-Based Configuration

Create different configurations for different roles:

**Developer**:
```bash
ENABLED_TOOLS=public_web_search,internal_search,cluster_inspect
```

**Operations**:
```bash
ENABLED_TOOLS=public_web_search,netra_search,cluster_inspect
```

**Support**:
```bash
ENABLED_TOOLS=public_web_search,dish_internal_tool,netra_search
```

**Admin**:
```bash
ENABLED_TOOLS=public_web_search,internal_search,netra_search,dish_internal_tool,cluster_inspect
```

## Security Best Practices

1. **Enable Only What's Needed**
   - Don't enable all tools by default
   - Review tool usage regularly

2. **Secure Credentials**
   - Store API keys securely
   - Use environment variables
   - Never commit credentials to git

3. **Audit Access**
   - Review tool usage logs
   - Monitor for suspicious activity
   - Set up alerts for sensitive tools

4. **Network Security**
   - Use VPN for internal tools
   - Restrict network access
   - Use firewalls

5. **Regular Reviews**
   - Review enabled tools quarterly
   - Update credentials regularly
   - Remove unused tools

## Troubleshooting

### Tool Not Working

1. Check if tool is enabled in `ENABLED_TOOLS`
2. Verify credentials are set
3. Check network connectivity
4. Review logs for errors

### Permission Denied

1. Verify credentials are correct
2. Check user has required permissions
3. Ensure network access is allowed
4. Contact administrator if needed

### Connection Timeouts

1. Check network connectivity
2. Verify URLs are correct
3. Check firewall rules
4. Verify VPN is connected (for internal tools)

## Examples

### Search Public Web
```bash
# User asks: "What's the weather in Denver?"
# Tool: public_web_search
# Query: "weather Denver"
```

### Search Internal Docs
```bash
# User asks: "Find the API documentation for user service"
# Tool: internal_search
# Query: "user service API documentation"
```

### Check Cluster Status
```bash
# User asks: "Are the sentry pods running?"
# Tool: cluster_inspect
# Command: "list sentry pods"
```

### Look Up Customer
```bash
# User asks: "Look up account 12345"
# Tool: dish_internal_tool
# Service: cart
# Endpoint: /api/search
# Params: {account: "12345"}
```

## API Reference

### Tool Call Format

All tools follow this format:

```python
result = tool_function(
    param1="value1",
    param2="value2"
)
```

### Return Format

All tools return JSON:

```json
{
  "success": true,
  "data": {...},
  "error": null
}
```

Or on error:

```json
{
  "success": false,
  "data": null,
  "error": "Error message"
}
```

## Support

For issues with tools:

1. Check this documentation
2. Review logs
3. Verify configuration
4. Contact your administrator

---

**Last Updated**: 2026-02-04  
**Version**: 1.0.0
