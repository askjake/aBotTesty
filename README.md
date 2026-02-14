# Chat-Agent Distribution Package

This directory contains everything needed to install Chat-Agent on Linux, Windows, or macOS.

## 📦 What's in This Directory

### Installation Packages
- `chat-agent-linux-installer.tar.gz` - Linux installer (all major distros)
- `chat-agent-windows-installer.zip` - Windows installer (Win10+, Server 2019+)
- `chat-agent-macos-installer.tar.gz` - macOS installer (macOS 11.0+)
- `chat-agent-universal-installer.tar.gz` - Universal package (all platforms)

### Documentation
- `INSTALLATION-SUMMARY.md` - Complete package overview
- `QUICKSTART-LINUX.md` - Linux quick start guide
- `QUICKSTART-WINDOWS.md` - Windows quick start guide
- `QUICKSTART-MACOS.md` - macOS quick start guide

### Utilities
- `verify-package.sh` - Verify package integrity

## 🚀 Quick Start

### 1. Choose Your Platform

**Linux Users**:
```bash
tar -xzf chat-agent-linux-installer.tar.gz
cd chat-agent-installer/installers/linux
sudo ./install.sh
```

**Windows Users**:
1. Extract `chat-agent-windows-installer.zip`
2. Right-click PowerShell → "Run as Administrator"
3. Navigate to `chat-agent-installer\installers\windows`
4. Run: `.\install.ps1` (or double-click `install.bat`)

**macOS Users**:
```bash
tar -xzf chat-agent-macos-installer.tar.gz
cd chat-agent-installer/installers/macos
./install.sh
```

### 2. Follow the Installation Wizard

The installer will:
- ✅ Install all dependencies (Python, Node.js, PostgreSQL)
- ✅ Set up the application
- ✅ Configure the database
- ✅ Let you choose which tools to enable
- ✅ Configure startup options
- ✅ Create system services

### 3. Access the Application

Once installed, open your browser:
```
http://localhost:3000
```

## 📋 Before You Install

### System Requirements
- **CPU**: 2+ cores (4+ recommended)
- **RAM**: 4GB minimum (8GB recommended)
- **Disk**: 10GB minimum (20GB recommended)
- **OS**: See platform-specific requirements below

### Platform-Specific Requirements

**Linux**:
- Ubuntu 20.04+, Debian 11+, CentOS 8+, RHEL 8+, or Fedora 35+
- sudo/root access
- systemd

**Windows**:
- Windows 10 or Windows Server 2019 or later
- PowerShell 5.1+
- Administrator privileges

**macOS**:
- macOS 11.0 (Big Sur) or later
- Xcode Command Line Tools (will be installed if needed)

### Network Requirements
- Internet access for dependency installation
- Ports 8000 and 3000 available
- VPN access (if using internal tools)

## 🔧 What Gets Installed

### Application Components
- **Backend**: Python FastAPI application (port 8000)
- **Frontend**: Next.js React application (port 3000)
- **Database**: PostgreSQL database
- **Services**: Automatic startup services

### Installation Locations

**Linux**:
- Application: `/opt/chat-agent`
- Configuration: `/etc/chat-agent`
- Logs: `/var/log/chat-agent`
- Data: `/var/lib/chat-agent`

**Windows**:
- Application: `C:\Program Files\ChatAgent`
- Configuration: `C:\ProgramData\ChatAgent`
- Logs: `C:\ProgramData\ChatAgent\Logs`

**macOS**:
- Application: `/Applications/ChatAgent`
- Configuration: `~/Library/Application Support/ChatAgent`
- Logs: `~/Library/Logs/ChatAgent`

## 🎯 Tool Configuration

During installation, you'll be asked which tools to enable:

- **public_web_search** - Search public internet (news, weather, etc.)
- **internal_search** - Search DISH internal systems (Confluence, JIRA, Git)
- **netra_search** - Search Netra logs and records
- **dish_internal_tool** - Access DISH internal tools (CART, CCTools)
- **cluster_inspect** - Kubernetes cluster inspection (read-only)

You can enable/disable tools based on your needs and permissions.

## 🔐 Security Considerations

### Before Installation
1. Review `security.md` in the package
2. Ensure you have secure passwords ready
3. Plan which tools you need
4. Verify network security requirements

### During Installation
1. Use strong passwords for database
2. Generate secure random keys (installer will help)
3. Only enable tools you need
4. Configure firewall rules

### After Installation
1. Review and secure configuration files
2. Set up monitoring
3. Configure backups
4. Test security controls

## 🆘 Troubleshooting

### Installation Fails
1. Check system requirements
2. Ensure you have admin/sudo access
3. Verify internet connectivity
4. Review error messages
5. Check the appropriate QUICKSTART guide

### Services Won't Start
1. Check logs (see QUICKSTART guide for location)
2. Verify database is running
3. Check port availability (8000, 3000)
4. Review configuration file

### Can't Access Application
1. Verify services are running
2. Check firewall settings
3. Ensure ports 8000 and 3000 are not blocked
4. Try accessing from localhost first

## 📚 Additional Resources

### In the Package
Each installer package includes:
- Complete README with detailed instructions
- Tool configuration guide
- Security best practices guide
- Utility scripts (health check, backup, update)

### After Extraction
```bash
# View main documentation
cat chat-agent-installer/README.md

# View tool configuration
cat chat-agent-installer/docs/tools-configuration.md

# View security guide
cat chat-agent-installer/docs/security.md
```

## ✅ Verify Package Integrity

Before installation, verify the package:

```bash
./verify-package.sh
```

This will check:
- All package files are present
- Documentation is complete
- Installer scripts exist
- Required files are in packages

## 📞 Support

### Self-Help
1. Read INSTALLATION-SUMMARY.md
2. Check platform-specific QUICKSTART guide
3. Review documentation in package
4. Check logs for errors

### Getting Help
1. Contact your system administrator
2. Provide error messages and logs
3. Note your platform and OS version
4. Describe what you were trying to do

## 🔄 Version Information

- **Version**: 1.0.0
- **Build Date**: 2026-02-04
- **Python**: 3.12+
- **Node.js**: 20+
- **PostgreSQL**: 14+

## 📝 Next Steps

1. **Verify Package** (optional but recommended)
   ```bash
   ./verify-package.sh
   ```

2. **Read Quick Start**
   - Open the QUICKSTART guide for your platform

3. **Extract Package**
   - Use the commands shown in "Quick Start" above

4. **Run Installer**
   - Follow the installation wizard

5. **Verify Installation**
   - Check services are running
   - Access http://localhost:3000
   - Run health check

6. **Secure Deployment**
   - Review security documentation
   - Implement security controls
   - Set up monitoring and backups

## 🎉 Ready to Install!

Choose your platform above and follow the Quick Start instructions.

For detailed information, see INSTALLATION-SUMMARY.md

---

**Package Location**: ~/aBotTesty  
**Total Size**: 4.27 MB  
**Platforms**: Linux, Windows, macOS  
**Ready for Distribution**: ✅
