
import discord
from discord import ui
from discord.ext import commands
from twelvedata import TDClient
import matplotlib.pyplot as plt
from io import BytesIO

import json
import datetime
import os



with open('data/config.json', 'r') as file:
    config = json.load(file)
token = config.get('token')
DATA_FILE = 'data/users.json'


td = TDClient(apikey=config.get('api_key'))


bot = commands.Bot(command_prefix="^", intents=discord.Intents.all())




bot.remove_command('help')


def fetch_data(user: discord.Member):
    """
    Opens the data.json file to look for the user's data.
    - If the user is not found, it creates an entry for them.
    - If the user's money is at zero and they have no shares, it resets their money to $100.
    """

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)


    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}


    user_id = str(user.id)

    if user_id not in data:
        data[user_id] = {
            "money": 100,
            "portfolio": {
                "shares": 0
            }
        }
    else:
        if data[user_id]["money"] <= 0 and not data[user_id]["portfolio"]:
            data[user_id]["money"] = 100


    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

    return data[user_id]

def save_data(user: discord.Member, updated_data: dict):
    """
    Saves the updated data for the specified user to data.json.
    """

    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)


    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = {}


    user_id = str(user.id)
    data[user_id] = updated_data


    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def purchase_stock(user: discord.Member, stock: str, shares: float):
    """
    This function buys X shares of stock for the user.
    """


    user_data = fetch_data(user)

    if "portfolio" not in user_data:
        user_data["portfolio"] = {}

    if "shares" not in user_data["portfolio"]:
        user_data["portfolio"]["shares"] = 0


    try:
        ts = td.time_series(symbol=stock, interval="1day", outputsize=365)
        data = ts.as_pandas()
        data.sort_index(inplace=True)
        current_price = data["close"].iloc[-1]
    except Exception as e:
        print(f"Error fetching stock price: {e}")
        return 0


    total_cost = current_price * shares


    if user_data["money"] < total_cost:
        return 0 

    user_data["money"] -= total_cost

    if stock in user_data["portfolio"]:
        user_data["portfolio"][stock]["shares"] += shares
    else:
        user_data["portfolio"][stock] = {"shares": shares}


    user_data["portfolio"]["shares"] += shares


    save_data(user, user_data)

    return 1  


class BuyStockButton(ui.View):
    '''
    This disgusting class just makes a button to buy shares of stock
    '''
    def __init__(self, user, symbol, current_price):
        super().__init__()
        self.user = user
        self.symbol = symbol
        self.current_price = current_price

    @ui.button(label="Buy Stock", style=discord.ButtonStyle.green)
    async def buy(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("You can't use this button!", ephemeral=True)
            return

        await interaction.response.send_message(f"How many shares of {self.symbol.upper()} would you like to buy?", ephemeral=True)

        def check(m):
            return m.author == self.user and m.channel == interaction.channel

        try:
            message = await interaction.client.wait_for("message", check=check, timeout=30)
            shares = float(message.content)

            if shares <= 0:
                await interaction.followup.send("Please enter a valid number of shares.", ephemeral=True)
                return

            total = shares * self.current_price

            if purchase_stock(self.user, self.symbol, shares) != 0:
                await interaction.followup.send(f"Successfully purchased {shares} shares of {self.symbol.upper()} at ${self.current_price:.2f} each. (${total:.2f})", ephemeral=True)
            else:
                await interaction.followup.send(f"Failed to purchase {shares} shares of {self.symbol.upper()} at ${self.current_price:.2f} each. (${total:.2f})", ephemeral=True)

        except Exception as e:
            print (e)
            await interaction.followup.send("Error processing your purchase.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Streaming(name="TS PMO", url="https://www.twitch.tv/morememes_"))

@bot.command()
async def help(ctx):
    """
    General help command
    """
    embed = discord.Embed(
        title="📘 Day Trader Bot - Help Menu",
        description="Simulate stock trading with fake money! Buy, sell, and manage your virtual portfolio.",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="💼 **What does it do?**",
        value="This bot allows you to trade real stocks using fake money. Compete with friends to see who can grow their portfolio the most!",
        inline=False
    )

    embed.add_field(
        name="💸 **How to make money?**",
        value=(
            "Everyone starts with $100. If your balance hits $0 and you hold no shares, your balance is reset to $100.\n"
            "Earn more by **buying low** and **selling high**!"
        ),
        inline=False
    )

    embed.add_field(
        name="📊 **Stock Command:**",
        value=(
            "`^stock <symbol> [interval] [outputsize]`\n"
            "➤ Use this command to check a stock's performance.\n"
            "➤ Click the **Buy Stock** button to purchase shares.\n"
            "**Examples:**\n"
            "`^stock TSLA` - Tesla stock (1-day interval)\n"
            "`^stock AAPL 1week 100` - Apple, weekly, 100 entries"
        ),
        inline=False
    )

    embed.add_field(
        name="👤 **User Command:**",
        value=(
            "`^user [@mention]`\n"
            "➤ Check your own or another user's portfolio.\n"
            "**Examples:**\n"
            "`^user` - View your portfolio\n"
            "`^user @username` - View someone else's portfolio"
        ),
        inline=False
    )

    embed.add_field(
        name="📉 **Sell Command:**",
        value=(
            "`^sell <symbol> <shares>`\n"
            "➤ Use this command to sell shares from your portfolio.\n"
            "**Examples:**\n"
            "`^sell TSLA 5` - Sell 5 Tesla shares\n"
            "`^sell AAPL 2` - Sell 2 Apple shares"
        ),
        inline=False
    )

    embed.set_footer(text="Happy trading! 📈")

    await ctx.send(embed=embed)

@bot.command()
async def user(ctx, user: discord.Member = None):
    """
    Gets the supplied user's info and portfolio.
    If no user is supplied, it grabs the one who sent the command.
    """

    if user is None:
        user = ctx.author

    user_data = fetch_data(user)

    current_balance = user_data['money']


    total_shares = sum(user_data['portfolio'][stock]['shares'] for stock in user_data['portfolio'] if stock != "shares")
    total_worth = 0


    for stock in user_data['portfolio']:
        if stock == "shares":
            continue  
        try:
            ts = td.time_series(symbol=stock, interval="1day", outputsize=365)
            data = ts.as_pandas()
            data.sort_index(inplace=True)
            current_price = data["close"].iloc[-1]
            total_worth += user_data['portfolio'][stock]['shares'] * current_price
        except Exception as e:
            print(f"Error fetching price for {stock}: {e}")


    embed = discord.Embed(
        title=f"{user.display_name}'s Portfolio",
        description=f"Current Balance: ${current_balance:.2f}",
        colour=0x00b0f4,
        timestamp=datetime.datetime.now()
    )
    embed.set_author(name=f"{user.display_name}'s Portfolio")
    embed.add_field(
        name="Current Portfolio",
        value=f"Total Stock Shares: {total_shares:.2f}\nTotal Worth: ${total_worth:.2f}",
        inline=False
    )

    await ctx.send(embed=embed)

    

@bot.command()
async def stock(ctx, symbol: str = None, interval: str = "1day", outputsize: int = 365):
    '''
    This command returns the supplied stock's history, current price, 1 month, and ytd
    Includes a button to buy the stock.
    '''

    if symbol is None:
        embed = discord.Embed(
            title="📊 Stock Command Usage",
            description="Fetch historical stock information with customizable intervals.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🛠️ **Usage:**",
            value="`^stock <symbol> [interval] [outputsize]`",
            inline=False
        )

        embed.add_field(
            name="📘 **Examples:**",
            value=(
                "`^stock TSLA` - Tesla stock (1-day interval)\n"
                "`^stock AAPL 1week 100` - Apple, weekly, 100 entries"
            ),
            inline=False
        )

        embed.add_field(
            name="⏳ **Supported Intervals:**",
            value="`1min`, `5min`, `15min`, `1day`, `1week`, `1month`",
            inline=False
        )

        embed.set_footer(text="Replace <symbol> with the stock ticker (e.g., TSLA, AAPL).")
        
        await ctx.send(embed=embed)
        return


    try:
        ts = td.time_series(symbol=symbol, interval=interval, outputsize=outputsize)
        data = ts.as_pandas()

        if data.empty:
            await ctx.send("No data found for that symbol.")
            return


        data.sort_index(inplace=True)


        current_price = data["close"].iloc[-1]


        month_ago_price = data["close"].iloc[-30] if len(data) >= 30 else data["close"].iloc[0]
        month_change = ((current_price - month_ago_price) / month_ago_price) * 100


        ytd_price = data["close"].iloc[0]
        ytd_change = ((current_price - ytd_price) / ytd_price) * 100


        plt.figure(figsize=(10, 5))
        plt.plot(data.index, data["close"], label=f"{symbol.upper()} Price")
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.title(f"{symbol.upper()} Stock History")
        plt.legend()
        plt.grid(True)

        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)
        plt.close()


        file = discord.File(buffer, filename="stock.png")

        embed = discord.Embed(title=f"{symbol.upper()} Stock Metrics", color=discord.Color.green())
        embed.set_image(url="attachment://stock.png")

        embed.add_field(name="Current Price", value=f"${current_price:.2f}", inline=False)
        embed.add_field(name="1 Month Change", value=f"{month_change:.2f}%", inline=False)
        embed.add_field(name="YTD Change", value=f"{ytd_change:.2f}%", inline=False)


        view = BuyStockButton(ctx.author, symbol, current_price)
        await ctx.send(file=file, embed=embed, view=view)
    
    except Exception as e:
        await ctx.send(f"Error getting requested stock ({symbol}).", ephemeral=True)

@bot.command()
async def sell(ctx, symbol: str = None, shares: float = None):
    """
    Sell a specified number of shares of a stock.
    Usage: ^sell <symbol> <shares>
    """

    if (symbol is None or shares is None):
        embed = discord.Embed(
            title="📉 Sell Command Usage",
            description="Use this command to sell shares from your portfolio.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="🛠️ **Usage:**",
            value="`^sell <symbol> <shares>`",
            inline=False
        )

        embed.add_field(
            name="📘 **Examples:**",
            value=(
                "`^sell TSLA 5` - Sell 5 Tesla shares\n"
                "`^sell AAPL 2` - Sell 2 Apple shares"
            ),
            inline=False
        )

        embed.set_footer(text="Replace <symbol> with the stock ticker (e.g., TSLA, AAPL).")
        
        await ctx.send(embed=embed)
        return



    user_data = fetch_data(ctx.author)


    symbol = symbol.lower()


    if symbol not in user_data["portfolio"]:
        await ctx.send(f"❌ You don't own any shares of {symbol.upper()}.")
        return


    available_shares = user_data["portfolio"][symbol]["shares"]
    if shares <= 0 or shares > available_shares:
        await ctx.send(f"❌ You only have {available_shares} shares of {symbol.upper()} available.")
        return

    try:

        ts = td.time_series(symbol=symbol, interval="1day", outputsize=1)
        data = ts.as_pandas()
        current_price = data["close"].iloc[-1]


        sale_amount = current_price * shares


        user_data["money"] += sale_amount
        user_data['portfolio']['shares'] -= shares
        user_data["portfolio"][symbol]["shares"] -= shares


        if user_data["portfolio"][symbol]["shares"] <= 0:
            del user_data["portfolio"][symbol]

        save_data(ctx.author, user_data)

        await ctx.send(f"✅ Sold {shares} shares of {symbol.upper()} for ${sale_amount:.2f}. Your new balance is ${user_data['money']:.2f}.")

    except Exception as e:
        await ctx.send(f"❌ Error processing the sale: {e}")


bot.run(token)