import config

import os
import time
import discord

from dotenv import load_dotenv

load_dotenv()
bot = discord.Bot()

from openai import OpenAI
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY')
)

user_tokens_today = {}
last_user_action = {}
prev_day_timestamp = 0

@bot.event
async def on_ready():
    print(f"{bot.user} is now online")

@bot.slash_command(name = "hello", description = "Say hello to the bot")
async def hello(ctx):
    await ctx.respond("What's up homie")

@bot.slash_command(name = "ask", description = "Ask a question")
@discord.guild_only()
@discord.commands.option(
    "prompt",
    description="Enter a prompt",
    required=True
)
async def ask(ctx, prompt=''):
    global prev_day_timestamp
    global user_tokens_today
    global last_user_action
    await ctx.response.defer()
    if time.time() > prev_day_timestamp + 86400: # reset the dictionaries if it's been over a day
        prev_day_timestamp = time.time()
        user_tokens_today = {}
        last_user_action = {}
    if prompt == '':
        await ctx.respond("Provide a valid prompt!")
        return
    print("-----")
    print(f"{ctx.author.id=}")
    print(f"{ctx.guild_id=}")
    print(f"{prompt=}")
    if len(prompt) > 200:
        print("Prompt too long")
        await ctx.respond("Prompt is too long.")
        return
    else:
        if ctx.author.id in user_tokens_today.keys() and user_tokens_today[ctx.author.id] >= config.USER_DAILY_TOKEN_LIMIT:
            print(f"{ctx.author.id} hit daily token limit")
            await ctx.respond(f"You have hit the daily token limit for today: {config.USER_DAILY_TOKEN_LIMIT}")
            return
        if ctx.author.id in last_user_action.keys() and last_user_action[ctx.author.id] >= time.time() - config.ACTION_COOLDOWN_SECS:
            print(f"{ctx.author.id} attempted action too soon")
            await ctx.respond(f"Wait {config.ACTION_COOLDOWN_SECS - (time.time() - last_user_action[ctx.author.id])} seconds")
            return
        if ctx.author.id not in config.ADMIN_USER_IDS:
            user_tokens_today[ctx.author.id] = 500 if ctx.author.id not in user_tokens_today.keys() else user_tokens_today[ctx.author.id] + 500
            last_user_action[ctx.author.id] = time.time()
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                { "role": "system", "content": config.GPT_SYSTEM_PROMPT },
                { "role": "user", "content": prompt }
            ],
            max_tokens=250
        )
        response_content = response.choices[0].message.content
        print(f"Generated response: {response.usage.prompt_tokens} + {response.usage.completion_tokens} = {response.usage.total_tokens}")
        embed = discord.Embed(
            title=f"`{prompt}`",
            description=response_content,
            color=discord.Colour.from_rgb(4, 184, 239)
        )
        if ctx.author.id not in config.ADMIN_USER_IDS:
            user_tokens_today[ctx.author.id] += response.usage.total_tokens - 500
        embed.add_field(name="Token cost", value=f"{response.usage.total_tokens} tokens")
        embed.add_field(name="Remaining daily tokens", value=f"{config.USER_DAILY_TOKEN_LIMIT - (0 if ctx.author.id not in user_tokens_today.keys() else max(user_tokens_today[ctx.author.id], 0))} tokens remaining")
        embed.set_footer(text="Texybot | Powered by GPT 3.5 Turbo", icon_url="https://imgur.com/yxn2ABK.png")
        await ctx.respond(embed=embed)
        return

bot.run(os.getenv('DISCORD_BOT_TOKEN')) # run the bot with the token