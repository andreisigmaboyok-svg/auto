import discord
from discord.ext import commands
import asyncio
import os
import json
import random
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

if TOKEN is None:
    print("EROARE: TOKEN nu a fost găsit în .env!")
    exit(1)

bot = commands.Bot(command_prefix="+", self_bot=True, reconnect=True, help_command=None)

STATE_FILE = "spam_state.json"

spam_l_channels = {}
spam_m_channels = {}
spam_task = None
active_autoreacts = {}

def save_state():
    state = {
        "spam_l": {},
        "spam_m": {},
        "active_autoreacts": active_autoreacts,
    }
    for ch_id, data in spam_l_channels.items():
        state["spam_l"][ch_id] = {
            "active": data.get("active", False),
            "index": data.get("index", 0),
            "user_id": data.get("user_id"),
            "delay": data.get("delay", 1.0),
            "messages": data.get("messages", [])
        }
    for ch_id, data in spam_m_channels.items():
        state["spam_m"][ch_id] = {
            "active": data.get("active", False),
            "index": data.get("index", 0),
            "user_ids": data.get("user_ids", []),
            "delay": data.get("delay", 2.0),
            "messages": data.get("messages", [])
        }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def load_state():
    global spam_l_channels, spam_m_channels, active_autoreacts
    if not os.path.isfile(STATE_FILE):
        return
    with open(STATE_FILE, "r") as f:
        state = json.load(f)
        spam_l_channels = {}
        for ch_id, data in state.get("spam_l", {}).items():
            spam_l_channels[ch_id] = {
                "active": data.get("active", False),
                "index": data.get("index", 0),
                "user_id": data.get("user_id"),
                "delay": data.get("delay", 1.0),
                "messages": data.get("messages", [])
            }
        spam_m_channels = {}
        for ch_id, data in state.get("spam_m", {}).items():
            spam_m_channels[ch_id] = {
                "active": data.get("active", False),
                "index": data.get("index", 0),
                "user_ids": data.get("user_ids", []),
                "delay": data.get("delay", 2.0),
                "messages": data.get("messages", [])
            }
        active_autoreacts = state.get("active_autoreacts", {})

async def spam_loop_l(channel_id):
    while True:
        data = spam_l_channels.get(str(channel_id))
        if not data or not data.get("active"):
            break
        channel = bot.get_channel(channel_id)
        if channel is None:
            break
        index = data.get("index", 0)
        messages = data.get("messages", [])
        user_id = data.get("user_id")
        delay = data.get("delay", 1.0)
        if not messages:
            break
        msg = messages[index]
        user = None
        if user_id:
            user = bot.get_user(user_id)
            if user is None:
                try:
                    user = await bot.fetch_user(user_id)
                except:
                    user = None
        try:
            if user:
                await channel.send(f"{user.mention} {msg}")
            else:
                await channel.send(msg)
        except:
            data["active"] = False
            save_state()
            break
        data["index"] = (index + 1) % len(messages)
        save_state()
        await asyncio.sleep(delay)

async def spam_loop_m(channel_id):
    while True:
        data = spam_m_channels.get(str(channel_id))
        if not data or not data.get("active"):
            break
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            break
        index = data.get("index", 0)
        messages = data.get("messages", [])
        user_ids = data.get("user_ids", [])
        delay = data.get("delay", 2.0)
        if not messages or not user_ids:
            break
        msg = messages[index]
        mentions_str = " ".join(f"<@{uid}>" for uid in user_ids)
        try:
            await channel.send(f"{mentions_str} {msg}")
        except:
            data["active"] = False
            save_state()
            break
        data["index"] = (index + 1) % len(messages)
        save_state()
        await asyncio.sleep(delay)

@bot.event
async def on_ready():
    print(f"{bot.user} este online!")
    load_state()
    for ch_id, data in spam_l_channels.items():
        if data.get("active"):
            spam_l_channels[ch_id]["task"] = asyncio.create_task(spam_loop_l(int(ch_id)))
            print(f"Reluat spam mare pe canal {ch_id}")
    for ch_id, data in spam_m_channels.items():
        if data.get("active"):
            spam_m_channels[ch_id]["task"] = asyncio.create_task(spam_loop_m(int(ch_id)))
            print(f"Reluat spam mic pe canal {ch_id}")

@bot.command()
async def lstart(ctx, member: discord.User = None, delay: float = 1.0):
    channel_id = str(ctx.channel.id)
    if channel_id in spam_l_channels and spam_l_channels[channel_id].get("active"):
        await ctx.message.add_reaction("❌")
        return
    try:
        with open("dume1.txt", "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await ctx.send("❌ Fișierul `dume1.txt` nu a fost găsit.")
        return
    spam_l_channels[channel_id] = {
        "active": True,
        "index": 0,
        "user_id": member.id if member else None,
        "delay": delay,
        "messages": messages
    }
    save_state()
    spam_l_channels[channel_id]["task"] = asyncio.create_task(spam_loop_l(ctx.channel.id))
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def lstop(ctx):
    channel_id = str(ctx.channel.id)
    if channel_id not in spam_l_channels or not spam_l_channels[channel_id].get("active"):
        await ctx.message.add_reaction("❌")
        return
    spam_l_channels[channel_id]["active"] = False
    task = spam_l_channels[channel_id].get("task")
    if task:
        task.cancel()
    save_state()
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def mstart(ctx, *args):
    channel_id = str(ctx.channel.id)
    if channel_id in spam_m_channels and spam_m_channels[channel_id].get("active"):
        await ctx.message.add_reaction("❌")
        return
    if len(args) < 2:
        await ctx.message.add_reaction("❌")
        return
    try:
        delay = float(args[-1])
    except:
        await ctx.message.add_reaction("❌")
        return
    user_mentions = args[:-1]
    user_ids = []
    for u in user_mentions:
        if u.startswith("<@") and u.endswith(">"):
            u_id = u.replace("<@!", "").replace("<@", "").replace(">", "")
            if u_id.isdigit():
                user_ids.append(int(u_id))
        elif u.isdigit():
            user_ids.append(int(u))
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, u)
                user_ids.append(member.id)
            except:
                pass
    if not user_ids:
        await ctx.message.add_reaction("❌")
        return
    try:
        with open("dume2.txt", "r", encoding="utf-8") as f:
            messages = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await ctx.send("❌ Fișierul `dume2.txt` nu a fost găsit.")
        return
    spam_m_channels[channel_id] = {
        "active": True,
        "index": 0,
        "user_ids": user_ids,
        "delay": delay,
        "messages": messages
    }
    save_state()
    spam_m_channels[channel_id]["task"] = asyncio.create_task(spam_loop_m(ctx.channel.id))
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def mstop(ctx):
    channel_id = str(ctx.channel.id)
    if channel_id not in spam_m_channels or not spam_m_channels[channel_id].get("active"):
        await ctx.message.add_reaction("❌")
        return
    spam_m_channels[channel_id]["active"] = False
    task = spam_m_channels[channel_id].get("task")
    if task:
        task.cancel()
    save_state()
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def pstart(ctx, *, args):
    global spam_task
    if spam_task and not spam_task.done():
        try:
            await ctx.message.add_reaction("❌")
        except:
            pass
        return
    try:
        parts = args.rsplit(" ", 1)
        mesaj = parts[0]
        delay = float(parts[1])
    except:
        try:
            await ctx.message.add_reaction("❌")
        except:
            pass
        return
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass
    async def spam_loop():
        while True:
            try:
                await ctx.send(mesaj)
                await asyncio.sleep(delay)
            except:
                break
    spam_task = asyncio.create_task(spam_loop())

@bot.command()
async def pstop(ctx):
    global spam_task
    if spam_task:
        spam_task.cancel()
        spam_task = None
        try:
            await ctx.message.add_reaction("✅")
            await ctx.message.delete()
        except:
            pass
    else:
        try:
            await ctx.message.add_reaction("❌")
        except:
            pass

@bot.command()
async def react(ctx, user: discord.User, emoji: str):
    global active_autoreacts
    active_autoreacts[user.id] = emoji
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass

@bot.command()
async def stop(ctx):
    global active_autoreacts
    try:
        user_id = ctx.author.id
        if user_id in active_autoreacts:
            del active_autoreacts[user_id]
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("✖️")
        try:
            await ctx.message.delete()
        except:
            pass
    except:
        pass

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot:
        return
    emoji = active_autoreacts.get(message.author.id)
    if emoji:
        try:
            await message.add_reaction(emoji)
        except:
            pass

# Comenzi troll & fake info

fake_names = [
    "Chastity Lazar", "Jordan Blake", "Taylor Morgan", "Skyler Quinn",
    "Riley Phoenix", "Casey Hunter", "Jamie Reese", "Avery Lane"
]

genders = ["Male", "Nigga", "Female", "Taran", "Other"]

hair_colors = ["Black", "Blonde", "Brown", "Red", "Gray", "White", "Blue"]

skin_colors = ["Black", "Brown", "Olive", "Tan", "Pale"]

locations = [
    "Kentucky", "California", "New York", "Texas", "Florida",
    "Washington", "Nevada", "Ohio", "Targoviste",
]

occupations = [
    "Artist", "Engineer", "Teacher", "Developer", "Designer",
    "Chef", "Musician", "Writer", "Curva", "Escorta"
]

ethnicities = [
    "Hispanic", "Non-Hispanic", "Asian", "African American",
    "Native American", "Pacific Islander"
]

religions = [
    "Christianity", "Hindu", "Islam", "Buddhism", "Atheist", "Jewish"
]

sexualities = [
    "Heterosexual", "Homosexual", "Bisexual", "Pansexual", "Asexual", "Gaay", "Transexual"
]

educations = [
    "High School", "College", "University", "Pre School", "Masters", "PhD"
]

passwords_examples = [
    "ilovefurries", "redskins32", "password1", "qwerty123", "letmein",
    "dragon", "sunshine", "football"
]

def age_to_str(age):
    if age < 16:
        words = {
            0:"zero",1:"unu",2:"doi",3:"trei",4:"patru",5:"cinci",
            6:"șase",7:"șapte",8:"opt",9:"nouă",10:"zece",11:"unsprezece",
            12:"doisprezece",13:"treisprezece",14:"paisprezece",15:"cincisprezece"
        }
        return words.get(age, str(age))
    else:
        return str(age)

@bot.command()
async def expose(ctx, user: discord.User = None):
    await ctx.message.delete()
    name = random.choice(fake_names)
    gender = random.choice(genders)
    age = random.randint(16, 45)
    height_ft = random.randint(4, 6)
    height_in = random.randint(0, 11)
    weight = random.randint(120, 300)
    hair_color = random.choice(hair_colors)
    skin_color = random.choice(skin_colors)
    dob_month = random.randint(1, 12)
    dob_day = random.randint(1, 28)
    dob_year = random.randint(1970, 2007)
    location = random.choice(locations)
    phone = f"({random.randint(100,999)})-{random.randint(100,999)}-{random.randint(1000,9999)}"
    email_name = name.lower().replace(" ", "_") + str(random.randint(1,99))
    email_domain = random.choice(["aol.com", "gmail.com", "yahoo.com", "hotmail.com"])
    email = f"{email_name}@{email_domain}"
    passwords = random.sample(passwords_examples, k=3)
    occupation = random.choice(occupations)
    salary = random.choice(["<$50,000", "$50,000-$100,000", ">$100,000"])
    ethnicity = random.choice(ethnicities)
    religion = random.choice(religions)
    sexuality = random.choice(sexualities)
    education = random.choice(educations)

    msg = (
        f"Successfully hacked user\n"
        f"Name: {name}\n"
        f"Gender: {gender}\n"
        f"Age: {age_to_str(age)}\n"
        f"Height: {height_ft}'{height_in}\"\n"
        f"Weight: {weight}\n"
        f"Hair Color: {hair_color}\n"
        f"Skin Color: {skin_color}\n"
        f"DOB: {dob_month}/{dob_day}/{dob_year}\n"
        f"Location: {location}\n"
        f"Phone: {phone}\n"
        f"E-Mail: {email}\n"
        f"Passwords: {passwords}\n"
        f"Occupation: {occupation}\n"
        f"Annual Salary: {salary}\n"
        f"Ethnicity: {ethnicity}\n"
        f"Religion: {religion}\n"
        f"Sexuality: {sexuality}\n"
        f"Education: {education}\n"
    )
    await ctx.send(f"```fix\n{msg}```")

fake_ips = [
    "192.168.1.100",
    "10.0.0.50",
    "172.16.254.1",
    "123.456.78.90",
]

@bot.command()
async def ip(ctx, user: discord.User = None):
    target = user.mention if user else "tu"
    fake_ip = random.choice(fake_ips)
    try:
        await ctx.message.add_reaction("🤣")
        await ctx.message.delete()
    except:
        pass
    await ctx.send(f"🕵️‍♂️ Ip ul lui {target} este: `{fake_ip}`")

@bot.command()
async def troll(ctx):
    await ctx.message.add_reaction("🤡")
    await ctx.message.delete()
    msgs = [
        "ce cauta ma la pula mea?",
        "moare tac tu bai pizda",
        "fut pe morti ma ti",
        "esti sageta la pula mea",
    ]
    await ctx.send(random.choice(msgs))

@bot.command()
async def play(ctx, *, text):
    try:
        await bot.change_presence(activity=discord.Game(name=text))
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Eroare la setarea statusului playing: {e}")

@bot.command()
async def playstop(ctx):
    try:
        await bot.change_presence(activity=None)
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Eroare la oprirea statusului playing: {e}")

@bot.command()
async def stream(ctx, *, text):
    try:
        await bot.change_presence(activity=discord.Streaming(name=text, url="https://twitch.tv/streamer"))
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Eroare la setarea statusului streaming: {e}")

async def streamstop(ctx):
    try:
        await bot.change_presence(activity=None)
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Eroare la oprirea statusului streaming: {e}")

@bot.command()
async def stopall(ctx):
    # Oprește toate spammările și reacțiile automate
    # Spam lstart
    for ch_id, data in spam_l_channels.items():
        data["active"] = False
        task = data.get("task")
        if task:
            task.cancel()
    # Spam mstart
    for ch_id, data in spam_m_channels.items():
        data["active"] = False
        task = data.get("task")
        if task:
            task.cancel()
    # Spam pstart
    global spam_task
    if spam_task:
        spam_task.cancel()
        spam_task = None
    # React auto
    active_autoreacts.clear()
    save_state()
    try:
        await ctx.message.add_reaction("✅")
        await ctx.message.delete()
    except:
        pass
    
@bot.command()
async def av(ctx, user: discord.User = None):
    await ctx.message.delete()
    if user is None:
        user = ctx.author

    avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
    await ctx.send(avatar_url)

@bot.command()
async def help(ctx):
    help_text = """```no category:
  react <@user/id> <emoji> - makes the bot react to the user with the emoji
  stop - stops the auto react
  lstart <@user> <delay> - start spamming big messages
  lstop - stop spamming big messages
  mstart <@user(s)> <delay> - start spamming small messages
  mstop - stop spamming small messages
  pstart <message> <delay> - start spamming a simple message
  pstop - stop spamming simple message
  expose [@user] - shows fake info about a user
  ip [@user] - shows a fake ip of a user
  troll - sends a random troll message
  stream <message> - set streaming status
  streamstop - stop streaming status
  play <text> - set playing status
  playstop - stop playing status
  stopall - stops everything thats running
  av - show user avatar
  help - shows this message
```"""
    await ctx.send(help_text)

bot.run(TOKEN)
