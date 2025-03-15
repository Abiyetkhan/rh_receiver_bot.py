import sqlite3
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

# Bot Token (Replace with your own)
TOKEN = "7785029656:AAEuFNlQW71Qonm96FeBzn3HPkRlMIg5jzI"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Set up logging
logging.basicConfig(level=logging.INFO)

# Connect to SQLite Database
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create user and sales tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    account_details TEXT,
    price REAL,
    status TEXT DEFAULT 'pending'
)
""")
conn.commit()

# Start Command
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    await message.reply("Welcome! Use /sell to list an account or /buy to purchase.")

# Sell Command
@dp.message_handler(commands=['sell'])
async def sell_cmd(message: types.Message):
    await message.reply("Send account details in this format: `username, followers, price`")

@dp.message_handler(lambda message: "," in message.text)
async def process_sale(message: types.Message):
    user_id = message.from_user.id
    details = message.text.split(',')

    if len(details) < 3:
        await message.reply("Invalid format. Use: `username, followers, price`")
        return

    username, followers, price = details[0].strip(), details[1].strip(), details[2].strip()
    cursor.execute("INSERT INTO sales (user_id, account_details, price) VALUES (?, ?, ?)",
                   (user_id, f"{username}, {followers} followers", float(price)))
    conn.commit()

    await message.reply(f"✅ Your account `{username}` is listed for ${price}.")

# Buy Command
@dp.message_handler(commands=['buy'])
async def list_accounts(message: types.Message):
    cursor.execute("SELECT sale_id, account_details, price FROM sales WHERE status='pending'")
    sales = cursor.fetchall()

    if not sales:
        await message.reply("❌ No accounts available for sale.")
        return

    response = "**Available Accounts:**\n"
    for sale in sales:
        response += f"🔹 `{sale[1]}` - **${sale[2]}** (ID: {sale[0]})\n"

    await message.reply(response + "\nUse `/purchase ID` to buy.")

# Purchase Command
@dp.message_handler(lambda message: message.text.startswith('/purchase'))
async def purchase_account(message: types.Message):
    try:
        sale_id = int(message.text.split()[1])
        user_id = message.from_user.id

        cursor.execute("SELECT user_id, price FROM sales WHERE sale_id=? AND status='pending'", (sale_id,))
        sale = cursor.fetchone()

        if not sale:
            await message.reply("❌ Invalid sale ID or already sold.")
            return

        seller_id, price = sale

        cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
        balance = cursor.fetchone()[0]

        if balance < price:
            await message.reply("❌ Insufficient balance.")
            return

        # Transfer funds
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (price, user_id))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (price, seller_id))
        cursor.execute("UPDATE sales SET status='sold' WHERE sale_id=?", (sale_id,))
        conn.commit()

        await message.reply(f"✅ Purchase successful! Account details will be shared soon.")
        await bot.send_message(seller_id, f"📢 Your account listing (ID: {sale_id}) has been sold!")

    except Exception as e:
        await message.reply("❌ Invalid command. Use `/purchase ID`.")

# Balance Check
@dp.message_handler(commands=['balance'])
async def check_balance(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]
    await message.reply(f"💰 Your balance: {balance} USDT.")

# Withdrawal
@dp.message_handler(commands=['withdraw'])
async def withdraw_cmd(message: types.Message):
    await message.reply("Enter amount and USDT address in this format: `amount USDT_WALLET`")

@dp.message_handler(lambda message: " " in message.text)
async def process_withdrawal(message: types.Message):
    user_id = message.from_user.id
    details = message.text.split()

    if len(details) < 2:
        await message.reply("Invalid format. Use: `amount USDT_WALLET`")
        return

    amount, wallet = float(details[0]), details[1]
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()[0]

    if amount > balance:
        await message.reply("❌ Insufficient balance.")
        return

    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (amount, user_id))
    conn.commit()

    await message.reply(f"✅ Withdrawal request for {amount} USDT to `{wallet}` submitted.")

# Run Bot
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
