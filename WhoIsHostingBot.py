import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz

TOKEN = 'YOUR_DISCORD_BOT_TOKEN'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Predefined schedule in UTC
schedule = []

# Generate times from 1PM today to 11AM tomorrow (Eastern Time)
start_time = datetime.now(pytz.timezone("US/Eastern")).replace(hour=13, minute=0, second=0, microsecond=0)
end_time = start_time + timedelta(days=1, hours=-2)

current_time = start_time
while current_time <= end_time:
    utc_time = current_time.astimezone(pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    schedule.append({"time": current_time.strftime("%I%p"), "utc_time": utc_time})
    current_time += timedelta(hours=2)

# Data structure to hold run sign-ups
signups = {}

def format_groups(time):
    """Format group information for display."""
    if time not in signups:
        return f"No sign-ups for {time}!"

    formatted = f"**{time} Run Groups:**\n"
    for host, details in signups[time].items():
        formatted += f"- Host: {host} | Actives: {', '.join(details['actives'])} | Alts: {', '.join(details['alts'])}\n"
    return formatted

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def help(ctx):
    """Robust help command to display all commands and their usage."""
    help_message = (
        "**Bot Commands:**\n"
        "`!times` - Display scheduled run times in your local time.\n"
        "`!join [time] [role] [host(optional) or name(s)]` - Join a run. Roles: 'host', 'active', 'alt'.\n"
        "    Example: `!join 1PM active @HostName`\n"
        "`!bulkjoin [role] [times] [host(optional) or names(optional)]` - Join multiple runs.\n"
        "    Example: `!bulkjoin host 1PM,5PM,7PM`\n"
        "`!groups [time]` - View groups for a specific run time.\n"
        "    Example: `!groups 1PM`\n"
        "`!allgroups` - View all groups for all scheduled runs.\n"
        "`!clear [time]` - Clear all sign-ups for a specific run.\n"
        "    Example: `!clear 1PM`\n"
    )
    await ctx.send(help_message)

@bot.command()
async def times(ctx):
    """Command to display run times in user's local time."""
    local_times = []
    for run in schedule:
        utc_time = datetime.strptime(run["utc_time"], "%Y-%m-%dT%H:%M:%SZ")
        unix_timestamp = int(utc_time.timestamp())
        local_times.append(f"{run['time']}: <t:{unix_timestamp}:f>")

    await ctx.send("**Scheduled Runs:**\n" + "\n".join(local_times))

@bot.command()
async def join(ctx, time: str, role: str, *names):
    """Command for players to join a run. Usage: !join [time] [role] [host(optional) or name(s)]"""
    if time not in [run["time"] for run in schedule]:
        await ctx.send(f"{time} is not a valid run time. Use `!times` to view available times.")
        return

    if time not in signups:
        signups[time] = {}

    player_name = ctx.author.mention

    if role.lower() == 'host':
        if player_name not in signups[time]:
            signups[time][player_name] = {"actives": [], "alts": []}
            await ctx.send(f"{player_name} has volunteered to host the {time} run!")
        else:
            await ctx.send(f"{player_name}, you are already hosting the {time} run!")
    elif role.lower() == 'active':
        if len(names) > 0:
            host = names[0]
            if host in signups[time]:
                signups[time][host]["actives"].append(player_name)
                await ctx.send(f"{player_name} has joined {host}'s group as an active player for {time}!")
            else:
                await ctx.send(f"{host} is not a registered host for {time}. Please choose an existing host or ask someone to volunteer.")
        else:
            await ctx.send(f"Please specify a host to join for {time}.")
    elif role.lower() == 'alt':
        if len(names) > 1:
            host = names[0]
            alts = names[1:]
            if host in signups[time]:
                signups[time][host]["alts"].extend(alts)
                await ctx.send(f"{', '.join(alts)} added as alts to {host}'s group for {time}!")
            else:
                await ctx.send(f"{host} is not a registered host for {time}. Please choose an existing host.")
        else:
            await ctx.send(f"Please specify a host and the alts to join for {time}.")
    else:
        await ctx.send("Invalid role! Use 'host', 'active', or 'alt'.")

@bot.command()
async def bulkjoin(ctx, role: str, times: str, *names):
    """Command for players to join multiple runs. Usage: !bulkjoin [role] [times] [host(optional) or names(optional)]"""
    times_list = times.split(",")
    player_name = ctx.author.mention

    for time in times_list:
        time = time.strip()
        if time not in [run["time"] for run in schedule]:
            await ctx.send(f"{time} is not a valid run time. Skipping...")
            continue

        if time not in signups:
            signups[time] = {}

        if role.lower() == 'host':
            if player_name not in signups[time]:
                signups[time][player_name] = {"actives": [], "alts": []}
                await ctx.send(f"{player_name} has volunteered to host the {time} run!")
            else:
                await ctx.send(f"{player_name}, you are already hosting the {time} run!")
        elif role.lower() == 'active':
            if len(names) > 0:
                host = names[0]
                if host in signups[time]:
                    signups[time][host]["actives"].append(player_name)
                    await ctx.send(f"{player_name} has joined {host}'s group as an active player for {time}!")
                else:
                    await ctx.send(f"{host} is not a registered host for {time}. Please choose an existing host or ask someone to volunteer.")
            else:
                await ctx.send(f"Please specify a host to join for {time}.")
        elif role.lower() == 'alt':
            if len(names) > 1:
                host = names[0]
                alts = names[1:]
                if host in signups[time]:
                    signups[time][host]["alts"].extend(alts)
                    await ctx.send(f"{', '.join(alts)} added as alts to {host}'s group for {time}!")
                else:
                    await ctx.send(f"{host} is not a registered host for {time}. Please choose an existing host.")
            else:
                await ctx.send(f"Please specify a host and the alts to join for {time}.")
        else:
            await ctx.send("Invalid role! Use 'host', 'active', or 'alt'.")

@bot.command()
async def groups(ctx, time: str):
    """Command to view groups for a specific time. Usage: !groups [time]"""
    await ctx.send(format_groups(time))

@bot.command()
async def allgroups(ctx):
