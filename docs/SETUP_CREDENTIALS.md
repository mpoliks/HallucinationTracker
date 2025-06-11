# 🔒 AWS SSO Authentication Setup

This project uses **AWS SSO (Single Sign-On)** for secure authentication. This is the recommended enterprise-grade approach that eliminates the need for long-lived access keys.

## 🎯 **Prerequisites**

You need:
- AWS CLI installed on your machine
- Access to your organization's AWS SSO portal
- Permission to access the required AWS services

## 🚀 **Setup Instructions**

### Step 1: Install AWS CLI (if needed)
```bash
# macOS
brew install awscli

# Linux/WSL  
pip install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### Step 2: Configure AWS SSO Profile
```bash
aws configure sso
```

**Use these settings:**
- **SSO session name**: `marek-admin` (or your preference)
- **SSO start URL**: `https://your-org.awsapps.com/start/#`
- **SSO region**: `us-east-1`
- **Default client Region**: `us-east-1`
- **CLI default output format**: `json`
- **Profile name**: `marek` ⚠️ **IMPORTANT: Must be exactly "marek"**

### Step 3: Test Your Setup
```bash
# Test authentication
aws sts get-caller-identity --profile marek

# Should show your user ARN and account info
```

## 🔄 **Daily Usage**

### When SSO Session Expires
Your SSO session will periodically expire. When it does:

```bash
aws sso login --profile marek
```

This will open your browser to re-authenticate.

### Check Session Status
```bash
aws sts get-caller-identity --profile marek
```

## ✅ **Verification**

After setup, your applications will show:
```
Debug: Using AWS SSO profile 'marek'...
✅ Successfully authenticated as: arn:aws:sts::123456789012:assumed-role/Administrator/your-email
```

## 🛠️ **Troubleshooting**

### Problem: "Profile 'marek' not found"
**Solution**: Re-run the SSO configuration
```bash
aws configure sso
# Make sure to use profile name: marek
```

### Problem: "SSO session expired"
**Solution**: Re-authenticate
```bash
aws sso login --profile marek
```

### Problem: "Access denied"
**Solution**: Check with your AWS administrator for proper permissions

## 🔒 **Security Benefits**

✅ **No long-lived access keys** stored on your machine  
✅ **Automatic token rotation** via SSO  
✅ **Centralized access management** by your organization  
✅ **Audit trail** of all access via CloudTrail  
✅ **Multi-factor authentication** enforced by SSO  

## 📝 **Configuration Files**

Your AWS configuration will be stored in:
- **macOS/Linux**: `~/.aws/config` and `~/.aws/credentials`
- **Windows**: `C:\Users\USERNAME\.aws\config` and `C:\Users\USERNAME\.aws\credentials`

The project will **only** use the `marek` profile - no fallback to environment variables or other profiles. 