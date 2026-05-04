# GitHub Setup & Deployment Guide

## 🚀 Sync with Your GitHub Repository

### 1. Initialize Git Repository
```bash
# Navigate to your project directory
cd C:\Projects\procure-me

# Initialize git (if not already done)
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Procure-Me pricing calculator with PDF parser"
```

### 2. Connect to Your GitHub Repository
```bash
# Add your remote repository
git remote add origin https://github.com/SuperGremlin25/Procure-Me.git

# Push to GitHub (first time)
git branch -M main
git push -u origin main
```

### 3. Verify GitHub Actions Are Working

1. Go to: https://github.com/SuperGremlin25/Procure-Me
2. Click on "Actions" tab
3. You should see these workflows:
   - ✅ Security Scan
   - ✅ Security Patches
   - ✅ CVE Scanner
   - ✅ Dependency Update
   - ✅ CodeQL Analysis

## 🛡️ Security Workflows Explained

### Security Scan (`security.yml`)
- **Triggers**: Push to main, PRs, daily at 2 AM UTC
- **Tools**: Bandit, Safety, Semgrep
- **What it does**: Scans Python code for security vulnerabilities
- **Reports**: Comments on PRs with findings

### Security Patches (`security-patches.yml`)
- **Triggers**: Push to main, PRs, daily at 5 AM UTC
- **Tools**: pip-audit, Safety
- **What it does**: Checks for available security patches
- **Reports**: Creates issues for critical vulnerabilities

### CVE Scanner (`cve-scan.yml`)
- **Triggers**: Push to main, PRs, every 6 hours
- **Tools**: pip-audit, Safety, Grype
- **What it does**: Scans for known CVEs in dependencies
- **Reports**: Aggregates findings from multiple scanners

### CodeQL Analysis (`codeql.yml`)
- **Triggers**: Push to main, PRs, weekly on Sundays
- **Tools**: GitHub CodeQL
- **What it does**: Advanced code analysis for security issues
- **Reports**: GitHub Security tab

### Dependency Update (`dependency-update.yml`)
- **Triggers**: Daily at 3 AM UTC, manual
- **Tools**: pip-review
- **What it does**: Automatically updates dependencies
- **Reports**: Creates PRs with updates

### Dependabot (`dependabot.yml`)
- **Triggers**: Daily (pip), weekly (GitHub Actions)
- **Tools**: GitHub Dependabot
- **What it does**: Automated dependency updates
- **Reports**: Creates PRs, assigns to you

## 📋 What You Need to Do

### 1. Enable GitHub Actions (if not enabled)
- Go to your repository on GitHub
- Click "Settings" tab
- Click "Actions" in left sidebar
- Ensure "Actions" are enabled

### 2. Enable Security Features
- In "Settings" > "Code security and analysis"
- Enable:
  - ✅ Dependabot alerts
  - ✅ Dependabot security updates
  - ✅ Code scanning (CodeQL)

### 3. (Optional) Add Snyk for Enhanced Scanning
1. Sign up at https://snyk.io/ (free tier available)
2. Get your API key
3. In GitHub repository > Settings > Secrets > Actions
4. Add new secret: `SNYK_TOKEN`
5. Uncomment Snyk lines in `cve-scan.yml`

### 4. Regular Maintenance
- **Review PRs**: Dependabot will create PRs for updates
- **Check Issues**: Security workflows may create issues
- **Monitor Actions**: Check Actions tab for any failures
- **Update Dependencies**: Review and merge dependency updates

## 🚨 Security Alerts

You'll receive alerts for:
- Critical CVEs in dependencies
- Security vulnerabilities in code
- Outdated dependencies with patches
- CodeQL security findings

## 📊 Security Dashboard

After first scan, check:
- GitHub Security tab (top of repository)
- Actions tab for detailed reports
- Dependabot alerts in Insights tab

## 🔧 Local Development Updates

When pulling updates:
```bash
# Get latest changes
git pull origin main

# Update local dependencies
pip install -r requirements.txt
```

## 🎯 Next Steps

1. Push your code to GitHub
2. Verify Actions are running
3. Check Security tab after first scan
4. Review any Dependabot PRs
5. Consider enabling Snyk (optional)

Your repository will be automatically monitored for security issues!