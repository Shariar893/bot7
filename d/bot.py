import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import requests
from bs4 import BeautifulSoup
import random
import time

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load token from environment variable or config file
import os
from dotenv import load_dotenv

# Load environment variables from .env file (create this file with TOKEN=your_token)
load_dotenv()

# Get token from environment variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("No token found! Make sure TELEGRAM_BOT_TOKEN is set in environment variables")

# List of earning methods with descriptions and points
EARNING_METHODS = [
    {
        'name': 'Watch Ads',
        'description': 'Watch short video ads and earn points',
        'points': random.randint(5, 20),
        'cooldown': 60
    },
    {
        'name': 'Complete Surveys',
        'description': 'Answer survey questions and earn rewards',
        'points': random.randint(50, 200),
        'cooldown': 300
    },
    {
        'name': 'Refer Friends',
        'description': 'Invite friends and get bonus when they join',
        'points': random.randint(100, 500),
        'cooldown': 0
    },
    {
        'name': 'Daily Bonus',
        'description': 'Claim your daily reward',
        'points': random.randint(10, 100),
        'cooldown': 86400
    },
    {
        'name': 'Play Mini Games',
        'description': 'Play simple games and earn points',
        'points': random.randint(20, 100),
        'cooldown': 180
    }
]

# User data storage (in a real app, use a database)
user_data = {}

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    if user_id not in user_data:
        user_data[user_id] = {
            'points': 0,
            'last_used': {},
            'referral_code': f"REF{user_id}",
            'referred_by': None,
            'referrals': 0
        }
    
    update.message.reply_text(
        f"👋 Hi {user.first_name}!\n\n"
        "💰 Welcome to the Advanced Earnings Bot!\n\n"
        "🔄 Use /earn to see earning methods\n"
        "📊 Use /balance to check your points\n"
        "🎁 Use /referral to get your invite link\n"
        "💸 Use /withdraw to cash out your earnings"
    )

def earn(update: Update, context: CallbackContext) -> None:
    """Show earning methods."""
    keyboard = []
    
    for i, method in enumerate(EARNING_METHODS):
        keyboard.append([InlineKeyboardButton(
            f"{method['name']} (+{method['points']} pts)", 
            callback_data=f"earn_{i}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "💡 Choose an earning method:",
        reply_markup=reply_markup
    )

def button(update: Update, context: CallbackContext) -> None:
    """Handle button presses."""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data.startswith("earn_"):
        method_index = int(data.split("_")[1])
        method = EARNING_METHODS[method_index]
        
        # Check cooldown
        last_used = user_data[user_id]['last_used'].get(method['name'], 0)
        current_time = time.time()
        
        if current_time - last_used < method['cooldown']:
            remaining = int(method['cooldown'] - (current_time - last_used))
            query.edit_message_text(
                f"⏳ Please wait {remaining} seconds before using '{method['name']}' again."
            )
            return
        
        # Add points
        points_earned = method['points']
        user_data[user_id]['points'] += points_earned
        user_data[user_id]['last_used'][method['name']] = current_time
        
        # Check for referral bonus
        if user_data[user_id]['referred_by'] and random.random() < 0.3:  # 30% chance for referral bonus
            bonus = int(points_earned * 0.1)  # 10% bonus
            user_data[user_id]['points'] += bonus
            points_earned += bonus
            query.edit_message_text(
                f"🎉 You earned {points_earned} points ({method['points']} + {bonus} referral bonus) from {method['name']}!\n\n"
                f"💰 Total points: {user_data[user_id]['points']}"
            )
        else:
            query.edit_message_text(
                f"🎉 You earned {points_earned} points from {method['name']}!\n\n"
                f"💰 Total points: {user_data[user_id]['points']}"
            )

def balance(update: Update, context: CallbackContext) -> None:
    """Show user's balance."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {'points': 0, 'last_used': {}}
    
    update.message.reply_text(
        f"💰 Your current balance: {user_data[user_id]['points']} points\n\n"
        f"👥 Referrals: {user_data.get(user_id, {}).get('referrals', 0)}\n"
        "🔗 Use /referral to invite friends and earn more!"
    )

def referral(update: Update, context: CallbackContext) -> None:
    """Generate referral link."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {'points': 0, 'last_used': {}, 'referral_code': f"REF{user_id}"}
    
    ref_code = user_data[user_id]['referral_code']
    ref_link = f"https://t.me/{(context.bot.username)}?start={ref_code}"
    
    update.message.reply_text(
        f"📢 Invite your friends and earn 10% of their earnings!\n\n"
        f"🔗 Your referral link:\n{ref_link}\n\n"
        f"👥 People invited: {user_data[user_id].get('referrals', 0)}\n"
        f"💸 You'll get bonus points when they use earning methods!"
    )

def withdraw(update: Update, context: CallbackContext) -> None:
    """Handle withdrawal requests."""
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = {'points': 0, 'last_used': {}}
    
    points = user_data[user_id]['points']
    
    if points < 1000:
        update.message.reply_text(
            f"❌ You need at least 1000 points to withdraw. You currently have {points} points.\n\n"
            "💡 Complete more tasks to earn more points!"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("PayPal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("Bitcoin", callback_data="withdraw_btc")],
        [InlineKeyboardButton("Gift Card", callback_data="withdraw_giftcard")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        "💸 Choose your withdrawal method (1000 points = $1):",
        reply_markup=reply_markup
    )

def handle_withdrawal(update: Update, context: CallbackContext) -> None:
    """Process withdrawal method selection."""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[1]
    
    query.edit_message_text(
        f"✉️ Please send your {method.upper()} details to the bot admin to process your withdrawal.\n\n"
        f"💰 You have {user_data[user_id]['points']} points available.\n"
        "⚠️ Withdrawals typically process within 24-48 hours."
    )

def process_start_with_referral(update: Update, context: CallbackContext) -> None:
    """Handle users who start with a referral code."""
    user = update.effective_user
    user_id = user.id
    args = context.args
    
    if args and args[0].startswith("REF"):
        referrer_code = args[0]
        referrer_id = int(referrer_code[3:])  # Extract ID from REF123
        
        # Initialize user data
        user_data[user_id] = {
            'points': 50,  # Bonus for using referral
            'last_used': {},
            'referral_code': f"REF{user_id}",
            'referred_by': referrer_id,
            'referrals': 0
        }
        
        # Add referral to referrer's count
        if referrer_id in user_data:
            user_data[referrer_id]['referrals'] = user_data.get(referrer_id, {}).get('referrals', 0) + 1
            user_data[referrer_id]['points'] += 100  # Referral bonus
        
        update.message.reply_text(
            f"🎉 Welcome {user.first_name}! You received 50 bonus points for using a referral link!\n\n"
            "💰 Use /earn to start making more points!"
        )
    else:
        start(update, context)

def error_handler(update: Update, context: CallbackContext) -> None:
    """Log errors."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

def main() -> None:
    """Start the bot."""
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", process_start_with_referral, pass_args=True))
    dispatcher.add_handler(CommandHandler("earn", earn))
    dispatcher.add_handler(CommandHandler("balance", balance))
    dispatcher.add_handler(CommandHandler("referral", referral))
    dispatcher.add_handler(CommandHandler("withdraw", withdraw))

    # Button handlers
    dispatcher.add_handler(CallbackQueryHandler(button, pattern="^earn_"))
    dispatcher.add_handler(CallbackQueryHandler(handle_withdrawal, pattern="^withdraw_"))

    # Error handler
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    # Modified startup for production hosting
    # Check if running on Render (production)
    if os.getenv('RENDER'):
        # Use webhook
        PORT = int(os.getenv('PORT', 3000))
        RENDER_URL = os.getenv('RENDER_EXTERNAL_URL')
        updater.start_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_URL}/{TOKEN}"
        )
    else:
        # Use polling for local development
        updater.start_polling()
    
    updater.idle()

if __name__ == '__main__':
    main()