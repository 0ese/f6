# Moonsec Deobfuscator Discord Bot

A Discord bot that deobfuscates Lua scripts protected by **Moonsec V3** obfuscator.

## Overview

This bot uses the [MoonsecDeobfuscator](https://github.com/tupsutumppu/MoonsecDeobfuscator) tool to deobfuscate Moonsec-protected Lua scripts. The deobfuscation process produces a **Lua 5.1 bytecode file**, which you can then decompile with your favorite Lua decompiler.

## Features

- Discord command: `.deobf` (with a `.lua` file upload)
- The bot processes and returns your deobfuscated script as a reply
- Deployable to [Render.com](https://render.com/) in a few clicks
- Automatic building of the .NET deobfuscator on first run

## Quick Start (Self-Host or Render)

### Prerequisites

- **.NET 8.0 SDK** (for building) or **.NET 8.0 Runtime** (for running)
- **Python 3.8+**
- **Discord Bot Token** (from [Discord Developer Portal](https://discord.com/developers/applications))

### Local Setup

1. **Clone this repo** and add your credentials:
   - Copy `.env.example` to `.env`
   - Paste your Discord bot token and client ID

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Clone the MoonsecDeobfuscator source:**
   ```bash
   git clone https://github.com/tupsutumppu/MoonsecDeobfuscator.git src
   ```

4. **Run the bot:**
   ```bash
   python bot.py
   ```

### Deploy to Render

1. **Push your code to GitHub** (make sure `src/` folder contains the MoonsecDeobfuscator source)

2. **Create a new Render Web Service:**
   - Source: Connect your GitHub repository
   - Environment: **Docker**
   - Root Directory: Leave blank (or use root)
   - Build Command: (automatically handled by Dockerfile)
   - Start Command: (automatically handled by Dockerfile)

3. **Add Environment Variables:**
   - `DISCORD_TOKEN` - Your Discord bot token
   - `DISCORD_CLIENT_ID` - Your bot's client ID

4. **Deploy!** Render will automatically:
   - Build the .NET MoonsecDeobfuscator
   - Install Python dependencies
   - Start the Discord bot

## Bot Usage

**In any server (with the bot invited):**
1. Type `.deobf` and attach your `.lua` file
2. Wait a few seconds for deobfuscation
3. The bot replies with your deobfuscated bytecode file, or an error if deobfuscation fails

## Environment Variables

- `DISCORD_TOKEN` — Your Discord bot token (never reveal this publicly!)
- `DISCORD_CLIENT_ID` — Your bot application/client ID

> **Security Tip:** Always keep your `.env` secret! Never commit your actual `.env`, only `.env.example`!

## Troubleshooting

- **Build fails**: Make sure the `src/` folder contains the complete MoonsecDeobfuscator source code
- **Timeout errors**: The file may be too complex or have infinite loops
- **Memory issues**: Render Free tier has 512MB RAM limit. Consider upgrading to a paid tier for larger files

## Credits

- **MoonsecDeobfuscator** by [tupsutumppu](https://github.com/tupsutumppu/MoonsecDeobfuscator) - The core deobfuscation engine

## License

This Discord bot wrapper is provided as-is. Please refer to the original MoonsecDeobfuscator repository for its license.

