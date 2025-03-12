from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes 


token = ""

example_device = None
target_device = None

is_setup_done = False

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello")


async def example_device_name_set (update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter example device name:")
    global example_device, target_device
    example_device = update.message.text
    print(f"Example device:{example_device}")

    if example_device and target_device != None:
        is_setup_done = True
        await update.message.reply_text("Setup is done")
    


async def target_device_name_set (update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter target device name:")
    global example_device, target_device
    target_device = update.message.text
    print(f"Target device:{target_device}")

    if example_device and target_device != None:
        is_setup_done = True
        await update.message.reply_text("Setup is done")
    


def handle_response (text:str) -> str:
    processed: str = text.lower()
    if "hello" in processed:
        return "hi!"
    print("Starting bot...")

if __name__ == "__main__":
    app = Application.builder().token(token).build()
    print("Starting bot...")

    # Commands
    app.add_handler(CommandHandler("start", start_command)) 
    app.add_handler(CommandHandler("example_set", example_device_name_set))
    app.add_handler(CommandHandler("target_set", target_device_name_set))

    #Polling
    print("Polling...")
    app.run_polling(poll_interval=3)
