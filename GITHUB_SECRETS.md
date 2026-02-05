# GitHub Secrets Configuration

This document lists all GitHub secrets required for SecureClaw's CI/CD pipeline.

## 📋 Quick Reference

| Secret Name | Required? | Purpose | Used In |
|-------------|-----------|---------|---------|
| `DISCORD_TOKEN` | ✅ **Required** | Production bot token | Integration tests, Discord E2E tests |
| `GEMINI_API_KEY` | ✅ **Required** | Gemini API for routing & embeddings | Integration tests, Discord E2E tests |
| `ANTHROPIC_API_KEY` | ⚠️ Optional | Claude API for complex tasks | Integration tests, Discord E2E tests |
| `OPENAI_API_KEY` | ⚠️ Optional | OpenAI API for complex tasks | Integration tests, Discord E2E tests |
| `TEST_DISCORD_BOT_TOKEN` | ⚠️ Optional | Test bot token for E2E tests | Discord E2E tests only |
| `TEST_DISCORD_CHANNEL_ID` | ⚠️ Optional | Test channel ID for E2E tests | Discord E2E tests only |

---

## 🎯 Required Secrets

### 1. DISCORD_TOKEN

**Purpose:** Your production Discord bot token for integration testing.

**How to get it:**
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to "Bot" section
4. Click "Reset Token" or copy existing token
5. Copy the token immediately (it won't be shown again)

**Format:** Three dot-separated parts totaling 70+ characters

**Security Notes:**
- This token grants full access to your bot
- Never commit this to version control
- Regenerate if accidentally exposed

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: DISCORD_TOKEN
Value: <your-token-here>
```

---

### 2. GEMINI_API_KEY

**Purpose:** Google Gemini API key for routing, embeddings, and simple queries.

**How to get it:**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Select or create a Google Cloud project
4. Copy the API key

**Format:** `AIzaSy...` followed by 33 alphanumeric characters

**Free Tier:**
- 60 requests per minute
- 1,500 requests per day
- Sufficient for CI/CD testing

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: GEMINI_API_KEY
Value: <your-api-key-here>
```

---

## ⚠️ Optional Secrets

### 3. ANTHROPIC_API_KEY (Optional)

**Purpose:** Claude API for handling complex tasks and code generation.

**Required for:**
- Testing Claude-based response generation
- If not provided, tests will use Gemini for all queries

**How to get it:**
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Navigate to "API Keys"
3. Click "Create Key"
4. Copy the API key

**Format:** `sk-ant-api03-` followed by 95-100 alphanumeric characters

**Pricing:**
- Pay-as-you-go
- Claude Sonnet 4.5: $3 per million input tokens, $15 per million output tokens
- CI usage: ~$0.10-0.50 per pipeline run

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: ANTHROPIC_API_KEY
Value: <your-api-key-here>
```

---

### 4. OPENAI_API_KEY (Optional)

**Purpose:** OpenAI API for alternative complex task handling.

**Required for:**
- Testing OpenAI-based response generation
- If not provided, tests will use Claude or Gemini

**How to get it:**
1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Click "Create new secret key"
3. Name it (e.g., "SecureClaw CI")
4. Copy the API key immediately

**Format:** `sk-proj-` followed by ~48 alphanumeric characters

**Pricing:**
- Pay-as-you-go
- GPT-4o: $2.50 per million input tokens, $10 per million output tokens
- CI usage: ~$0.05-0.30 per pipeline run

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: OPENAI_API_KEY
Value: <your-api-key-here>
```

---

### 5. TEST_DISCORD_BOT_TOKEN (Optional)

**Purpose:** Separate Discord bot token for end-to-end testing with real Discord API.

**Required for:**
- Discord E2E tests (`test_discord_e2e.py`)
- Testing real bot responses, slash commands, and message handling
- If not provided, Discord E2E tests are skipped

**How to get it:**
1. Create a **separate** Discord application for testing
2. Go to [Discord Developer Portal](https://discord.com/developers/applications)
3. Click "New Application"
4. Name it "SecureClaw Test Bot"
5. Go to "Bot" section
6. Copy the bot token

**Important:**
- Use a DIFFERENT bot than your production bot
- Add this test bot to a dedicated test server
- Give it minimal permissions (Read Messages, Send Messages)

**Format:** Same as `DISCORD_TOKEN`

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: TEST_DISCORD_BOT_TOKEN
Value: <your-test-bot-token-here>
```

---

### 6. TEST_DISCORD_CHANNEL_ID (Optional)

**Purpose:** Discord channel ID where the test bot will send messages.

**Required for:**
- Discord E2E tests alongside `TEST_DISCORD_BOT_TOKEN`
- If not provided, Discord E2E tests are skipped

**How to get it:**
1. Enable Developer Mode in Discord:
   - User Settings → Advanced → Developer Mode (toggle ON)
2. Right-click the test channel
3. Click "Copy Channel ID"

**Format:** `1234567890123456789` (18-19 digits)

**Important:**
- Use a dedicated test channel
- The test bot must have access to this channel
- Messages will be posted during CI runs

**Add to GitHub:**
```bash
Settings → Secrets and variables → Actions → New repository secret
Name: TEST_DISCORD_CHANNEL_ID
Value: <your-channel-id-here>
```

---

## 🚀 Quick Setup Guide

### Minimum Required Setup (Integration Tests Only)

To run integration tests (Docker services, mocked Discord):

```bash
# Required
DISCORD_TOKEN=<your-production-bot-token>
GEMINI_API_KEY=<your-gemini-api-key>

# Optional (improves test coverage)
ANTHROPIC_API_KEY=<your-claude-api-key>
OPENAI_API_KEY=<your-openai-api-key>
```

**Result:** ✅ Lint, Type Check, Security, Tests, Docker Build, Integration Tests will pass

---

### Full Setup (All Tests Including Discord E2E)

To run all tests including real Discord API tests:

```bash
# Required
DISCORD_TOKEN=<your-production-bot-token>
GEMINI_API_KEY=<your-gemini-api-key>

# Optional but recommended
ANTHROPIC_API_KEY=<your-claude-api-key>
OPENAI_API_KEY=<your-openai-api-key>

# For Discord E2E tests
TEST_DISCORD_BOT_TOKEN=<your-test-bot-token>
TEST_DISCORD_CHANNEL_ID=<your-test-channel-id>
```

**Result:** ✅ All CI/CD jobs pass including Discord E2E tests

---

## 📝 Adding Secrets to GitHub

### Via GitHub Web UI

1. Go to your repository on GitHub
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Enter the **Name** (exactly as shown above)
6. Enter the **Value** (your API key/token)
7. Click **Add secret**

### Via GitHub CLI

```bash
# Required secrets
gh secret set DISCORD_TOKEN
gh secret set GEMINI_API_KEY

# Optional secrets
gh secret set ANTHROPIC_API_KEY
gh secret set OPENAI_API_KEY
gh secret set TEST_DISCORD_BOT_TOKEN
gh secret set TEST_DISCORD_CHANNEL_ID
```

You'll be prompted to paste the value for each secret.

---

## 🔍 Verifying Secrets

### Check Which Secrets Are Set

```bash
gh secret list
```

### Test in CI

Push a commit and check the GitHub Actions tab. Look for:

- ✅ **Integration Tests**: Should pass with just `DISCORD_TOKEN` and `GEMINI_API_KEY`
- ⏭️ **Discord E2E Tests**: Will be skipped if `TEST_DISCORD_BOT_TOKEN` not set
- 📊 **Summary**: Shows which tests ran and which were skipped

### Example Output

**With minimum secrets:**
```
✅ Linting & Formatting
✅ Type Checking
✅ Security Scanning
✅ Unit Tests (Python 3.12)
✅ Unit Tests (Python 3.13)
✅ Docker Build
✅ Integration Tests
⏭️ Discord E2E Tests (skipped - secrets not configured)
```

**With all secrets:**
```
✅ Linting & Formatting
✅ Type Checking
✅ Security Scanning
✅ Unit Tests (Python 3.12)
✅ Unit Tests (Python 3.13)
✅ Docker Build
✅ Integration Tests
✅ Discord E2E Tests
```

---

## 🔐 Security Best Practices

### DO ✅

- Use separate test bot tokens from production
- Regenerate tokens if accidentally exposed
- Use API keys with minimal required permissions
- Monitor API usage dashboards for unexpected activity
- Set up billing alerts for paid APIs

### DON'T ❌

- Never commit secrets to version control
- Never share secrets in Discord, Slack, or email
- Never use production bot tokens in public CI
- Never skip secret rotation after team member departures
- Never set secrets as environment variables in CI config files

---

## 💰 Cost Estimates

### Monthly Cost for CI/CD Only

**Assuming 50 pushes/month:**

| Service | Usage | Cost |
|---------|-------|------|
| Gemini API | 100-200 requests/run | **Free** (within free tier) |
| Anthropic Claude | 50-100 requests/run | ~$5-10/month |
| OpenAI GPT-4o | 50-100 requests/run | ~$3-7/month |
| Discord API | Unlimited | **Free** |

**Total: $0-17/month** depending on which APIs you enable.

### Reducing Costs

1. **Use only Gemini**: Set only `DISCORD_TOKEN` and `GEMINI_API_KEY`
   - Cost: **$0/month** ✅
   - Trade-off: Less comprehensive testing

2. **Skip Discord E2E**: Don't set `TEST_DISCORD_BOT_TOKEN`
   - Saves: API calls to Discord + LLM costs for real responses
   - Trade-off: No real Discord API testing

3. **Use `[skip integration]` in commit messages**: Skip integration tests for docs-only changes
   - Example: `git commit -m "docs: update README [skip integration]"`

---

## 🆘 Troubleshooting

### "Discord E2E Tests" not running

**Cause:** `TEST_DISCORD_BOT_TOKEN` or `TEST_DISCORD_CHANNEL_ID` not set.

**Solution:** These are optional. If you want to run E2E tests, add both secrets.

### "Integration Tests" failing with auth errors

**Cause:** `DISCORD_TOKEN` or `GEMINI_API_KEY` invalid or missing.

**Solution:**
1. Verify secrets are set: `gh secret list`
2. Regenerate tokens if expired
3. Check for typos in secret names (case-sensitive!)

### API rate limit errors

**Cause:** Too many CI runs hitting API limits.

**Solution:**
1. Use `[skip integration]` for non-code changes
2. Increase API quotas (Gemini: upgrade plan)
3. Add delays between retries in code

### "Secret not found" errors

**Cause:** Secret name mismatch or not set at repository level.

**Solution:**
- Secret names are **case-sensitive**
- Must be set at repository level (not environment)
- Use exact names from this guide

---

## 📚 Additional Resources

- [GitHub Encrypted Secrets Docs](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [Discord Developer Portal](https://discord.com/developers/docs)
- [Google AI Studio](https://makersuite.google.com/)
- [Anthropic Console](https://console.anthropic.com/)
- [OpenAI Platform](https://platform.openai.com/)

---

## 🔄 Last Updated

**Date:** 2026-02-06
**CI/CD Version:** v1.0.0
**SecureClaw Version:** Phases 1-4 complete

---

## Questions?

If you have issues with secrets configuration:
1. Check [Troubleshooting](#-troubleshooting) section above
2. Review [CI/CD Documentation](docs/CI_CD.md)
3. Open an issue on [GitHub](https://github.com/jimtin/sercureclaw/issues)
