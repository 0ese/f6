# Quick Deployment Guide

## ✅ What's Ready

All files are created and ready for deployment:

- ✅ `bot.py` - Discord bot that handles `.deobf` commands
- ✅ `Dockerfile` - Builds .NET deobfuscator and runs Python bot
- ✅ `requirements.txt` - Python dependencies
- ✅ `README.md` - Full documentation
- ✅ `SETUP.md` - Detailed setup instructions
- ✅ `.gitignore` - Ignores sensitive files

## ⚠️ What You Need to Do

### 1. Get the MoonsecDeobfuscator Source

You need to download/clone the MoonsecDeobfuscator source code into the `src/` folder.

**Option A: Manual Download**
1. Go to: https://github.com/tupsutumppu/MoonsecDeobfuscator
2. Click "Code" → "Download ZIP"
3. Extract the ZIP
4. Rename folder to `src`
5. Move `src/` into `Moonsec Deobfuscator/` folder

**Option B: Using Git (if installed)**
```bash
cd "Moonsec Deobfuscator"
git clone https://github.com/tupsutumppu/MoonsecDeobfuscator.git src
```

### 2. Create `.env` File

Create a file named `.env` in the `Moonsec Deobfuscator/` folder:

```
DISCORD_TOKEN=your-discord-bot-token-here
DISCORD_CLIENT_ID=your-client-id-here
```

### 3. Upload to GitHub

1. Create a new GitHub repository
2. Upload the entire `Moonsec Deobfuscator/` folder contents
3. Make sure the `src/` folder is included!

### 4. Deploy on Render

1. Go to https://render.com
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Environment**: `Docker`
   - **Root Directory**: Leave blank
   - **Build Command**: (auto-handled by Dockerfile)
   - **Start Command**: (auto-handled by Dockerfile)
5. Add Environment Variables:
   - `DISCORD_TOKEN` = (your bot token)
   - `DISCORD_CLIENT_ID` = (your client ID)
6. Click "Create Web Service"

## 🚀 You're Done!

Once deployed, your bot will:
- Accept `.deobf` commands with .lua file attachments
- Deobfuscate Moonsec-protected files
- Return the deobfuscated bytecode

## 📝 Notes

- The Dockerfile automatically builds the .NET deobfuscator during deployment
- Free tier on Render has 512MB RAM - may need upgrade for larger files
- First deployment may take 5-10 minutes (building .NET project)

