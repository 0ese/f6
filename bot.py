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
from urllib.parse import urlparse, unquote
from aiohttp import web
import aiohttp

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

# Server and role restrictions
ALLOWED_SERVER_ID = 1441808704876970026
ADMIN_ROLE_ID = 1441808742957056092

# Token management
TOKENS_FILE = 'tokens.json'
SETTINGS_FILE = 'settings.json'
INITIAL_TOKENS = 3
DAILY_TOKENS = 2
COST_PER_USE = 1

# File cleanup tracking
pending_cleanup_files = []

async def cleanup_file_after_delay(filepath, delay_seconds=120):
    """Delete a file after specified delay (default 2 minutes)"""
    await asyncio.sleep(delay_seconds)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"Cleaned up file: {filepath}")
            if filepath in pending_cleanup_files:
                pending_cleanup_files.remove(filepath)
    except Exception as e:
        print(f"Error cleaning up file {filepath}: {e}")

def schedule_file_cleanup(filepath, delay_seconds=120):
    """Schedule a file for cleanup after delay"""
    pending_cleanup_files.append(filepath)
    asyncio.create_task(cleanup_file_after_delay(filepath, delay_seconds))

def load_settings():
    """Load bot settings"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {'token_system_enabled': True}
    return {'token_system_enabled': True}

def save_settings(settings):
    """Save bot settings"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=2)

def is_token_system_enabled():
    """Check if token system is currently enabled"""
    settings = load_settings()
    return settings.get('token_system_enabled', True)

def set_token_system(enabled):
    """Enable or disable the token system"""
    settings = load_settings()
    settings['token_system_enabled'] = enabled
    save_settings(settings)

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
    """Extract and aggressively clean URLs from text to ensure Discord compatibility"""
    cleaned_links = []
    
    # Split by 'http' to handle merged URLs
    parts = text.split('http')
    
    for part in parts:
        if not part:
            continue
        
        # Reconstruct the URL with http/https
        if part.startswith('://'):
            link = 'http' + part
        elif part.startswith('s://'):
            link = 'https' + part[1:]
        else:
            continue
        
        try:
            # Step 1: Remove everything after common terminators
            for terminator in ['\n', '\r', '\t', ' ', '"', "'", '<', '>', '{', '}', '|', '\\', '^', '`', '[', ']']:
                if terminator in link:
                    link = link.split(terminator)[0]
            
            # Step 2: Stop at next URL if URLs are concatenated
            # Look for common URL start patterns after the domain
            for pattern in ['http://', 'https://']:
                if link.count(pattern) > 1:
                    # Find the position of the second occurrence
                    first_pos = link.find(pattern)
                    second_pos = link.find(pattern, first_pos + len(pattern))
                    if second_pos > 0:
                        link = link[:second_pos]
            
            # Step 3: Aggressively remove trailing special characters
            while link and link[-1] in '.,;:)]}!?"\'>\\|`~@#$%^&*+=':
                link = link[:-1]
            
            # Step 4: Remove URL-encoded characters that might cause issues
            link = unquote(link)
            
            # Step 5: Remove any non-printable ASCII characters
            link = ''.join(char for char in link if 32 <= ord(char) <= 126)
            
            # Step 6: Ensure it's still a valid URL structure
            if not link.startswith(('http://', 'https://')):
                continue
            
            # Step 7: Parse URL to validate structure
            parsed = urlparse(link)
            if not parsed.scheme or not parsed.netloc:
                continue
            
            # Step 8: Skip bot's Discord link
            if 'discord.gg/Y3yt5XMCGj' in link:
                continue
            
            # Step 9: Final validation - must have protocol and domain
            if len(link) > 10 and '://' in link and '.' in parsed.netloc:
                cleaned_links.append(link)
                
        except Exception:
            # If any error occurs, skip this link
            continue
    
    # Remove duplicates while preserving order
    seen = set()
    unique_links = []
    for link in cleaned_links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)
    
    return unique_links

def is_valid_url(url):
    """Check if a string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

async def download_file_from_url(url):
    """Download file content from URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    content = await response.read()
                    # Check file size (5MB limit)
                    if len(content) > 5 * 1024 * 1024:
                        return None, "File too large! Maximum size is 5MB."
                    return content, None
                else:
                    return None, f"Failed to download file. HTTP Status: {response.status}"
    except asyncio.TimeoutError:
        return None, "Download timed out. Please try again."
    except Exception as e:
        return None, f"Error downloading file: {str(e)}"

def check_server_restriction():
    """Check if command is used in allowed server"""
    async def predicate(ctx):
        if ctx.guild is None:
            await ctx.reply('❌ This bot only works in the authorized server!')
            return False
        if ctx.guild.id != ALLOWED_SERVER_ID:
            await ctx.reply('❌ This bot is not authorized to work in this server!')
            return False
        return True
    return commands.check(predicate)

def check_admin_role():
    """Check if user has the admin role"""
    async def predicate(ctx):
        if ctx.guild is None:
            return False
        has_role = any(role.id == ADMIN_ROLE_ID for role in ctx.author.roles)
        if not has_role:
            await ctx.reply('❌ You do not have permission to use this command!')
        return has_role
    return commands.check(predicate)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print(f'Token system enabled: {is_token_system_enabled()}')
    print('Bot is ready!')

@bot.command()
@check_server_restriction()
async def help(ctx):
    """Show available commands"""
    embed = discord.Embed(
        title="🤖 Bot Commands",
        description="Use these commands to interact with the bot:",
        color=0x5865F2
    )
    embed.add_field(
        name="`.deobf`",
        value="Deobfuscate a Moonsec V3 obfuscated Lua file\n**Usage:** \n• `.deobf` (attach a .lua or .txt file)\n• `.deobf <url>` (provide a direct link to the file)",
        inline=False
    )
    
    if is_token_system_enabled():
        embed.add_field(
            name="`.creds`",
            value="Check your remaining tokens",
            inline=False
        )
    
    if is_token_system_enabled():
        embed.set_footer(text="Each deobfuscation costs 1 token. You receive 2 free tokens daily.")
    else:
        embed.set_footer(text="⚠️ Token system is currently DISABLED - Free deobfuscations for everyone!")
    
    await ctx.reply(embed=embed)

@bot.command()
@check_server_restriction()
async def creds(ctx):
    """Show user's remaining tokens"""
    user_id = ctx.author.id
    tokens = get_user_tokens(user_id)
    
    if not is_token_system_enabled():
        embed = discord.Embed(
            title="💰 Your Credits",
            description=f"You have **{tokens} token(s)** saved.\n\n⚠️ **Token system is currently DISABLED**\nDeobfuscations are FREE for everyone!",
            color=0xFFA500
        )
        embed.set_footer(text="Your tokens are safe and will be restored when token system is enabled again!")
    else:
        embed = discord.Embed(
            title="💰 Your Credits",
            description=f"You have **{tokens} token(s)** remaining.",
            color=0x00FF00 if tokens > 0 else 0xFF0000
        )
        embed.set_footer(text="You receive 2 free tokens every day!")
    
    await ctx.reply(embed=embed)

@bot.command()
@check_server_restriction()
async def gift(ctx, user_id: int = None, amount: int = None):
    """Gift tokens to another user"""
    if not is_token_system_enabled():
        await ctx.reply('❌ Token system is currently disabled! Gifting is not available.')
        return
    
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
    
    for _ in range(amount):
        use_token(gifter_id)
    
    add_tokens(user_id, amount)
    
    embed = discord.Embed(
        title="🎁 Gift Sent!",
        description=f"Successfully gifted **{amount} token(s)** to <@{user_id}>!",
        color=0x00FF00
    )
    await ctx.reply(embed=embed)

@bot.command()
@check_server_restriction()
@check_admin_role()
async def token(ctx, status: str = None):
    """Enable or disable the token system (Admin only)"""
    if status is None:
        current_status = "ENABLED" if is_token_system_enabled() else "DISABLED"
        embed = discord.Embed(
            title="🎫 Token System Status",
            description=f"Current status: **{current_status}**\n\nUsage:\n• `.token on` - Enable token system\n• `.token off` - Disable token system (free for all)",
            color=0x00FF00 if is_token_system_enabled() else 0xFF0000
        )
        await ctx.reply(embed=embed)
        return
    
    status = status.lower()
    
    if status == 'on':
        if is_token_system_enabled():
            await ctx.reply('⚠️ Token system is already enabled!')
            return
        
        set_token_system(True)
        embed = discord.Embed(
            title="✅ Token System Enabled",
            description="The token system has been **enabled**!\n\n• Users will need tokens to deobfuscate files\n• All saved tokens have been restored\n• Daily token rewards are active",
            color=0x00FF00
        )
        embed.set_footer(text=f"Enabled by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
        print(f"Token system ENABLED by {ctx.author} ({ctx.author.id})")
        
    elif status == 'off':
        if not is_token_system_enabled():
            await ctx.reply('⚠️ Token system is already disabled!')
            return
        
        set_token_system(False)
        embed = discord.Embed(
            title="🔓 Token System Disabled",
            description="The token system has been **disabled**!\n\n• Deobfuscations are now FREE for everyone\n• User tokens are saved and will be restored when re-enabled\n• Daily token rewards are paused",
            color=0xFFA500
        )
        embed.set_footer(text=f"Disabled by {ctx.author.display_name}")
        await ctx.reply(embed=embed)
        print(f"Token system DISABLED by {ctx.author} ({ctx.author.id})")
        
    else:
        await ctx.reply('❌ Invalid option! Use `.token on` or `.token off`')

@bot.command()
@check_server_restriction()
async def deobf(ctx, url: str = None):
    """
    Usage: .deobf (attach a .lua/.txt file) OR .deobf <url>
    Deobfuscates a Moonsec Lua obfuscated file and returns the result.
    """
    user_id = ctx.author.id
    token_system_active = is_token_system_enabled()
    
    if token_system_active:
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
    
    # Check if URL is provided
    file_content = None
    filename = None
    original_size = 0
    from_url = False
    
    if url:
        # Validate URL
        if not is_valid_url(url):
            await ctx.reply('❌ Invalid URL! Please provide a valid http:// or https:// URL.')
            return
        
        loading_msg = await ctx.reply("<a:Loading:1447156037885886525> Downloading and deobfuscating the file from URL...")
        
        # Download file from URL
        file_content, error = await download_file_from_url(url)
        if error:
            await loading_msg.edit(content=f'❌ {error}')
            return
        
        # Extract filename from URL
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename or not (filename.endswith('.lua') or filename.endswith('.txt')):
            filename = 'script.lua'
        
        original_size = len(file_content)
        from_url = True
        
    elif ctx.message.attachments:
        # Use attached file
        attachment = ctx.message.attachments[0]
        
        if not (attachment.filename.endswith('.lua') or attachment.filename.endswith('.txt')):
            await ctx.reply('❌ Only .lua and .txt files are supported!')
            return

        if attachment.size > 5 * 1024 * 1024:
            await ctx.reply('❌ File too large! Maximum size is 5MB.')
            return
        
        loading_msg = await ctx.reply("<a:Loading:1447156037885886525> Deobfuscating the file...")
        
        filename = attachment.filename
        original_size = attachment.size
        from_url = False
        
    else:
        await ctx.reply('❌ Please either attach a .lua/.txt file OR provide a URL!\n**Examples:**\n• `.deobf` (with file attached)\n• `.deobf https://example.com/script.lua`')
        return
    
    file_ext = '.lua' if filename.endswith('.lua') else '.txt'
    input_fd, input_path = tempfile.mkstemp(suffix=file_ext)
    output_fd, output_path = tempfile.mkstemp(suffix='_deobf.lua')
    os.close(input_fd)
    os.close(output_fd)
    
    # Only schedule cleanup for URL downloads (2 minutes)
    if from_url:
        schedule_file_cleanup(input_path, delay_seconds=120)
        schedule_file_cleanup(output_path, delay_seconds=120)
    
    try:
        # Save file content to temp file
        if file_content:
            # From URL
            with open(input_path, 'wb') as f:
                f.write(file_content)
        else:
            # From attachment
            await ctx.message.attachments[0].save(input_path)
        
        project_dir = os.path.dirname(os.path.abspath(__file__))
        bin_dir = os.path.join(project_dir, 'bin')
        
        deobf_exe = None
        
        if os.path.exists(bin_dir):
            for root, dirs, files in os.walk(bin_dir):
                for file in files:
                    if file == 'MoonsecDeobfuscator' or file == 'MoonsecDeobfuscator.exe':
                        deobf_exe = os.path.join(root, file)
                        break
                if deobf_exe:
                    break
        
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
            await ctx.reply('❌ Moonsec deobfuscator executable not found. Please ensure the project is built.')
            return
        
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
                await ctx.reply('❌ Could not find MoonsecDeobfuscator project file.')
                return
        else:
            cmd = [
                deobf_exe,
                '-dev',
                '-i', input_path,
                '-o', output_path
            ]
        
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
            await loading_msg.edit(embed=embed, content=None)
            return
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1:
            if token_system_active:
                use_token(user_id)
                remaining_tokens = get_user_tokens(user_id)
            else:
                remaining_tokens = get_user_tokens(user_id)
            
            with open(output_path, 'r', encoding='utf-8', errors='ignore') as f:
                output_content = f.read()
            
            found_links = extract_links(output_content)
            
            output_size = os.path.getsize(output_path)
            
            if output_size > 25 * 1024 * 1024:
                await ctx.reply(f'❌ Deobfuscated file is too large ({output_size / 1024 / 1024:.1f}MB). Discord limit is 25MB.')
                return
            
            embed = discord.Embed(
                title="✅ Deobfuscation Complete",
                description=f"Successfully deobfuscated {filename}",
                color=0x00FF00
            )
            
            if url:
                embed.add_field(
                    name="🔗 Source",
                    value=f"[Original File]({url})",
                    inline=False
                )
            
            stats_text = (f"**Original Size:** {original_size / 1024:.2f} KB\n"
                         f"**Deobfuscated Size:** {output_size / 1024:.2f} KB\n"
                         f"**Processing Time:** {processing_time:.2f}s\n")
            
            if token_system_active:
                stats_text += f"**Tokens Left:** {remaining_tokens} tokens"
            else:
                stats_text += f"**Tokens Saved:** {remaining_tokens} tokens\n⚠️ **FREE MODE** - No tokens used!"
            
            embed.add_field(
                name="📊 Statistics",
                value=stats_text,
                inline=False
            )
            
            if found_links:
                links_text = '\n'.join(found_links[:10])
                if len(found_links) > 10:
                    links_text += f"\n... and {len(found_links) - 10} more"
                embed.add_field(
                    name="🔗 Found Links",
                    value=links_text,
                    inline=False
                )
            
            # Different footer based on source
            if from_url:
                embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')} • Temp files auto-delete in 2min")
            else:
                embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
            
            view = discord.ui.View()
            decompile_button = discord.ui.Button(
                label="Decompile The Output Code",
                style=discord.ButtonStyle.link,
                url="https://luadec.metaworm.site/"
            )
            view.add_item(decompile_button)
            
            try:
                await loading_msg.delete()
            except:
                pass
            
            await ctx.reply(
                embed=embed,
                file=discord.File(output_path, filename=f"deobf_{filename}"),
                view=view
            )
        else:
            embed = discord.Embed(
                title="❌ Deobfuscation Failed",
                description="⚠️ **Only Moonsec V3 supported**\n\nMake sure you're uploading a valid Moonsec V3 obfuscated file.",
                color=0xFF0000
            )
            embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
            await loading_msg.edit(embed=embed, content=None)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Deobfuscation Failed",
            description=f"⚠️ **Internal Error**\n\nAn error occurred: {str(e)[:200]}",
            color=0xFF0000
        )
        embed.set_footer(text=f"Requested by {ctx.author.display_name} - {datetime.now().strftime('%m/%d/%y, %I:%M %p')}")
        try:
            await loading_msg.edit(embed=embed, content=None)
        except:
            await ctx.reply(embed=embed)
    finally:
        # Immediate cleanup for attachment-based deobfuscations
        if not from_url:
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

# HTTP server for Render (required for free tier web services)
async def health_check(request):
    return web.Response(text="Bot is running!")

async def start_http_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    port = int(os.getenv('PORT', 10000))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'HTTP server running on port {port}')

async def main():
    # Start HTTP server first (for Render health checks)
    await start_http_server()
    # Then start the Discord bot
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
