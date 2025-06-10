# 🔒 AWS Credential Setup Guide

This project now supports multiple secure ways to provide AWS credentials, in order of preference:

## 🏆 **RECOMMENDED: AWS CLI Profile**

The most secure and convenient approach for local development:

### Step 1: Install AWS CLI (if not already installed)
```bash
# macOS
brew install awscli

# Linux/WSL
pip install awscli

# Windows
# Download from: https://aws.amazon.com/cli/
```

### Step 2: Configure ToggleBank Profile
```bash
aws configure --profile togglebank
```

You'll be prompted for:
- **AWS Access Key ID**: `your-access-key-id`
- **AWS Secret Access Key**: `your-secret-access-key`
- **Default region**: `us-east-1` (recommended)
- **Default output format**: `json` (recommended)

### Step 3: Verify Setup
```bash
aws sts get-caller-identity --profile togglebank
```

✅ **That's it!** The application will automatically use the `togglebank` profile.

## 🥈 **ALTERNATIVE: Default AWS Profile**

If you prefer to use your default AWS configuration:

```bash
aws configure
# Enter your credentials
```

## 🥉 **FALLBACK: Environment Variables**

**Not recommended for security reasons, but supported as fallback:**

```bash
# In your shell profile (.zshrc, .bashrc, .bash_profile)
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

## 🔍 **Credential Priority Order**

The application tries credential sources in this order:

1. **AWS CLI Profile (`togglebank`)**
2. **Default AWS CLI Profile**
3. **Environment Variables**
4. **IAM Roles** (when running on AWS infrastructure)

## 🔧 **Troubleshooting**

### Profile Not Found
```bash
# List available profiles
aws configure list-profiles

# Create the togglebank profile
aws configure --profile togglebank
```

### Invalid Credentials
```bash
# Test your credentials
aws sts get-caller-identity --profile togglebank

# Reconfigure if needed
aws configure --profile togglebank
```

### Permission Errors
Ensure your AWS user has the following permissions:
- `bedrock:*`
- `bedrock-agent:*`
- `sts:GetCallerIdentity`

## ✅ **Benefits of AWS CLI Profiles**

- 🔐 **Secure**: Credentials stored in `~/.aws/credentials` (not in code)
- 🔄 **Automatic rotation**: Supports AWS credential rotation
- 👥 **Multiple accounts**: Easy switching between AWS accounts
- 🛠️ **Standard practice**: Works with all AWS tools and SDKs
- 🚀 **Production ready**: Same approach used in production environments

## 🚫 **Security Notes**

- ❌ **Never commit** AWS credentials to git
- ❌ **Don't use** `.env` files for production credentials
- ✅ **Use IAM roles** for production deployments
- ✅ **Rotate credentials** regularly
- ✅ **Use least privilege** principle for IAM permissions 