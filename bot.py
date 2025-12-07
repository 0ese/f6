import os
import discord
import tempfile
import asyncio
import subprocess
import json
import re
from datetime import datetime, timedelta
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.dm_messages = True
bot = commands.Bot(command_prefix='.', intents=intents, help_command=None)

# Token management
TOKENS_FILE = 'tokens.json'
INITIAL_TOKENS = 3
DAILY_TOKENS = 2
COST_PER_USE = 1

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        try:
            with open(TOKENS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_tokens(tokens):
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)

def get_user_tokens(user_id):
    tokens_data = load_tokens()
    user_id_str = str(user_id)
    
    if user_id_str not in tokens_data:
        tokens_data[user_id_str] = {
            'tokens': INITIAL_TOKENS,
            'last_daily': None
        }
        save_tokens(tokens_data)
    
    user_data = tokens_data[user_id_str]
    
    # Check if we need to give daily tokens
    now = datetime.now()
    last_daily = user_data.get('last_daily')
    
    if last_daily:
        last_daily_date = datetime.fromisoformat(last_daily)
        # If it's a new day, give daily tokens
        if now.date() > last_daily_date.date():
            user_data['tokens'] = user_data.get('tokens', 0) + DAILY_TOKENS
            user_data['last_daily'] = now.isoformat()
            save_tokens(tokens_data)
    else:
        # First time, set last_daily to now
        user_data['last_daily'] = now.isoformat()
        save_tokens(tokens_data)
    
    return user_data['tokens']

def use_token(user_id):
    tokens_data = load_tokens()
    user_id_str = str(user_id)
    
    tokens = get_user_tokens(user_id)
    if tokens < COST_PER_USE:
        return False
    
    tokens_data[user_id_str]['tokens'] = tokens - COST_PER_USE
    save_tokens(tokens_data)
    return True

def add_tokens(user_id, amount):
    tokens_data = load_tokens()
    user_id_str = str(user_id)
    
    if user_id_str not in tokens_data:
        tokens_data[user_id_str] = {
            'tokens': INITIAL_TOKENS,
            'last_daily': None
        }
    
    tokens_data[user_id_str]['tokens'] = tokens_data[user_id_str].get('tokens', 0) + amount
    save_tokens(tokens_data)

def extract_links(text):
    """Extract URLs from text"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    links = re.findall(url_pattern, text)
    return list(set(links))  # Remove duplicates

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Bot is ready!')

@bot.command()
async def help(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="🤖 Moonsec Deobfuscator Bot - Commands",
        description="Use these commands to interact with the bot:",
        color=0x5865F2
    )
    embed.add_field(
        name="`.deobf`",
        value="Deobfuscate a Moonsec V3 obfuscated Lua file\nUsage: `.deobf` (attach a .lua or .txt file)",
        inline=False
    )
    embed.add_field(
        name="`.creds`",
        value="Check your remaining tokens",
        inline=False
    )
    embed.add_field(
        name="`.gift <user_id> <amount>`",
        value="Gift tokens to another user\nExample: `.gift 1024565710128689202 100`",
        inline=False
    )
    embed.add_field(
        name="`.help`",
        value="Show this help message",
        inline=False
    )
    embed.set_footer(text="Each deobfuscation costs 1 token. You receive 2 free tokens daily.")
    await ctx.reply(embed=embed)

@bot.command()
async def creds(ctx):
    """Show user's remaining tokens"""
    user_id = ctx.author.id
    tokens = get_user_tokens(user_id)
    
    embed = discord.Embed(
        title="💰 Your Credits",
        description=f"You have **{tokens} token(s)** remaining.",
        color=0x00FF00 if tokens > 0 else 0xFF0000
    )
    embed.set_footer(text="You receive 2 free tokens every day!")
    await ctx.reply(embed=embed)

@bot.command()
async def gift(ctx, user_id: int = None, amount: int = None):
    """Gift tokens to another user"""
    if user_id is None or amount is None:
        await ctx.reply('❌ Usage: `.gift <user_id> <amount>`\nExample: `.gift 1024565710128689202 100`')
        return
    
    if amount <= 0:
        await ctx.reply('❌ Amount must be greater than 0!')
        return
    
    gifter_id = ctx.author.id
    gifter_tokens = get_user_tokens(gifter_id)
    
    if gifter_tokens < amount:
        await ctx.reply(f'❌ You don\'t have enough tokens! You only have {gifter_tokens} token(s).')
        return
    
    # Deduct from gifter
    for _ in range(amount):
        use_token(gifter_id)
    
    # Add to recipient
    add_tokens(user_id, amount)
    
    embed = discord.Embed(
        title="🎁 Gift Sent!",
        description=f"Successfully gifted **{amount} token(s)** to <@{user_id}>!",
        color=0x00FF00
    )
    await ctx.reply(embed=embed)

@bot.command()
async def deobf(ctx):
    """
    Usage: .deobf (attach a .lua file)
    Deobfuscates a Moonsec Lua obfuscated file and returns the result.
    """
    # Check tokens
    user_id = ctx.author.id
    tokens = get_user_tokens(user_id)
    
    if tokens < COST_PER_USE:
        embed = discord.Embed(
            title="❌ Deobfuscation Failed",
            description="⚠️ **Insufficient Tokens**\n\nYou don't have enough tokens to use this command.\n\nUse `.creds` to check your token balance.",
            color=0xFF0000
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
        await ctx.reply(embed=embed)
        return
    
    # Find attachment
    if not ctx.message.attachments:
        await ctx.reply('Please upload file using the command')
        return
    attachment = ctx.message.attachments[0]
    if not (attachment.filename.endswith('.lua') or attachment.filename.endswith('.txt')):
        await ctx.reply('Only .lua and .txt files are supported!')
        return

    # Check file size first (limit to 5MB to prevent memory issues)
    if attachment.size > 5 * 1024 * 1024:
        await ctx.reply('File too large! Maximum size is 5MB.')
        return
    
    await ctx.reply(f"Received `{attachment.filename}`. Processing... (this may take up to 90 seconds)")
    
    # Download file - determine extension from original filename
    file_ext = '.lua' if attachment.filename.endswith('.lua') else '.txt'
    input_fd, input_path = tempfile.mkstemp(suffix=file_ext)
    output_fd, output_path = tempfile.mkstemp(suffix='_deobf.lua')
    os.close(input_fd)
    os.close(output_fd)
    
    try:
        await attachment.save(input_path)
        
        # Find the Moonsec deobfuscator executable
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(project_dir, 'bin')
        
        # Try to find the built executable (built by Dockerfile)
        deobf_exe = None
        
        # Search in bin directory (where Dockerfile copies it)
        if os.path.exists(bin_dir):
            for root, dirs, files in os.walk(bin_dir):
                for file in files:
                    if file == 'MoonsecDeobfuscator' or file == 'MoonsecDeobfuscator.exe':
                        deobf_exe = os.path.join(root, file)
                        break
                if deobf_exe:
                    break
        
        # Also check common locations including .NET 9.0 paths
        if not deobf_exe:
            src_dir = os.path.join(project_dir, 'src')
            possible_paths = [
                os.path.join(project_dir, 'MoonsecDeobfuscator'),
                os.path.join(project_dir, 'MoonsecDeobfuscator.exe'),
                os.path.join(src_dir, 'bin', 'Release', 'net9.0', 'MoonsecDeobfuscator'),
                os.path.join(src_dir, 'bin', 'Release', 'net9.0', 'MoonsecDeobfuscator.exe'),
                os.path.join(src_dir, 'bin', 'Release', 'net8.0', 'MoonsecDeobfuscator'),
                os.path.join(src_dir, 'bin', 'Release', 'net8.0', 'MoonsecDeobfuscator.exe'),
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    deobf_exe = path
                    break
        
        # Try using dotnet run as fallback
        if not deobf_exe:
            src_dir = os.path.join(project_dir, 'src')
            csproj_path = None
            if os.path.exists(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith('.csproj') and 'Moonsec' in file:
                            csproj_path = os.path.join(root, file)
                            break
                    if csproj_path:
                        break
            
            if csproj_path:
                deobf_exe = 'dotnet'
        
        if not deobf_exe:
            await ctx.reply('Moonsec deobfuscator executable not found. Please ensure the project is built.')
            return
        
        # Call Moonsec deobfuscator
        if deobf_exe == 'dotnet':
            csproj_path = None
            src_dir = os.path.join(project_dir, 'src')
            if os.path.exists(src_dir):
                for root, dirs, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith('.csproj') and 'Moonsec' in file:
                            csproj_path = os.path.join(root, file)
                            break
                    if csproj_path:
                        break
            if csproj_path:
                cmd = [
                    'dotnet', 'run', '--project', csproj_path, '--',
                    '-dev',
                    '-i', input_path,
                    '-o', output_path
                ]
            else:
                await ctx.reply('Could not find MoonsecDeobfuscator project file.')
                return
        else:
            cmd = [
                deobf_exe,
                '-dev',
                '-i', input_path,
                '-o', output_path
            ]
        
        # Run subprocess in executor to avoid blocking Discord event loop
        def run_deobfuscator():
            return subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=90,
                cwd=os.path.dirname(deobf_exe) if deobf_exe != 'dotnet' and os.path.dirname(deobf_exe) else project_dir
            )
        
        start_time = datetime.now()
        try:
            result = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(None, run_deobfuscator),
                timeout=95
            )
        except asyncio.TimeoutError:
            embed = discord.Embed(
                title="❌ Deobfuscation Failed",
                description="⚠️ **Timeout**\n\nDeobfuscation timed out after 90 seconds. The file may be too complex or have infinite loops.",
                color=0xFF0000
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
            await ctx.reply(embed=embed)
            return
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Read output or error
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1:
            # Use token
            use_token(user_id)
            remaining_tokens = get_user_tokens(user_id)
            
            # Read output file
            with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
                output_content = f.read()
            
            # Extract links from output
            found_links = extract_links(output_content)
            
            # Check output file size (Discord has 25MB limit)
            output_size = os.path.getsize(output_path)
            original_size = attachment.size
            
            if output_size > 25 * 1024 * 1024:
                await ctx.reply(f'Deobfuscated file is too large ({output_size / 1024 / 1024:.1f}MB). Discord limit is 25MB.')
                return
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Deobfuscation Complete",
                description=f"Successfully deobfuscated {attachment.filename}",
                color=0x00FF00
            )
            
            # Add statistics
            embed.add_field(
                name="📊 Statistics",
                value=f"**Original Size:** {original_size / 1024:.2f} KB\n"
                      f"**Deobfuscated Size:** {output_size / 1024:.2f} KB\n"
                      f"**Processing Time:** {processing_time:.2f}s\n"
                      f"**Tokens Left:** {remaining_tokens} tokens",
                inline=False
            )
            
            # Add found links if any
            if found_links:
                links_text = '\n'.join([f"• `{link}`" for link in found_links[:10]])  # Limit to 10 links
                if len(found_links) > 10:
                    links_text += f"\n... and {len(found_links) - 10} more"
                embed.add_field(
                    name="🔗 Found Links",
                    value=links_text,
                    inline=False
                )
            
            embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
            
            # Create view with decompile button
            view = discord.ui.View()
            decompile_button = discord.ui.Button(
                label="Decompile The Output Code",
                style=discord.ButtonStyle.link,
                url="https://luadec.metaworm.site/"
            )
            view.add_item(decompile_button)
            
            # Send file with embed
            await ctx.reply(
                embed=embed,
                file=discord.File(output_path, filename=f"deobf_{attachment.filename}"),
                view=view
            )
        else:
            # Failed deobfuscation
            embed = discord.Embed(
                title="❌ Deobfuscation Failed",
                description="⚠️ **Only Moonsec V3 supported**\n\nMake sure you're uploading a valid Moonsec V3 obfuscated file.",
                color=0xFF0000
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
            await ctx.reply(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Deobfuscation Failed",
            description=f"⚠️ **Internal Error**\n\nAn error occurred: {str(e)[:200]}",
            color=0xFF0000
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
        await ctx.reply(embed=embed)
    finally:
        try:
            if os.path.exists(input_path):
                os.remove(input_path)
        except Exception:
            pass
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except Exception:
            pass

bot.run(TOKEN)
