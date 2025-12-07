# Setup Instructions for Moonsec Deobfuscator Discord Bot

## Getting the MoonsecDeobfuscator Source Code

Since you need to include the MoonsecDeobfuscator source code, you have two options:

### Option 1: Using Git (Recommended)

If you have Git installed:
```bash
cd "Moonsec Deobfuscator"
git clone https://github.com/tupsutumppu/MoonsecDeobfuscator.git src
```

### Option 2: Manual Download

1. Go to https://github.com/tupsutumppu/MoonsecDeobfuscator
2. Click the green **"Code"** button
3. Click **"Download ZIP"**
4. Extract the ZIP file
5. Rename the extracted folder to `src`
6. Move the `src` folder into your `Moonsec Deobfuscator` project folder

### Verify Structure

After getting the source code, your folder structure should look like:

```
Moonsec Deobfuscator/
├── bot.py
├── requirements.txt
├── Dockerfile
├── README.md
├── .env.example
├── .gitignore
└── src/
    ├── MoonsecDeobfuscator.csproj
    ├── MoonsecDeobfuscator.sln
    └── (other source files)
```

## Environment Setup

1. Copy `.env.example` to `.env`
2. Edit `.env` and add your Discord bot credentials:
   ```
   DISCORD_TOKEN=your-discord-bot-token-here
   DISCORD_CLIENT_ID=your-client-id-here
   ```

## Testing Locally (Optional)

If you want to test locally before deploying:

1. Install .NET 8.0 SDK
2. Install Python 3.8+
3. Install Python dependencies: `pip install -r requirements.txt`
4. Build the deobfuscator: `cd src && dotnet build -c Release`
5. Run the bot: `python bot.py`

## Deployment to Render

1. **Push everything to GitHub** (including the `src/` folder)
2. **Create a new Render Web Service**
   - Environment: **Docker**
   - Root Directory: Leave blank
   - Add environment variables:
     - `DISCORD_TOKEN`
     - `DISCORD_CLIENT_ID`
3. **Deploy!** Render will automatically build everything.

## Troubleshooting

- **Build fails on Render**: Make sure the `src/` folder contains the complete MoonsecDeobfuscator source
- **Executable not found**: The Dockerfile should build it automatically. Check build logs.
- **Timeout errors**: Large or complex files may timeout. Consider upgrading Render tier.

