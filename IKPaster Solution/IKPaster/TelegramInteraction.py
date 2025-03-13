from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, Updater


token = ""

FIRST_QUESTION, SECOND_QUESTION = range(2)
user_answers = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answers.clear
    await update.message.reply_text("Hi, give me an example device name:")
    return FIRST_QUESTION


async def example_device_name_set (update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_answers['example_device'] = update.message.text
    
    update.message.reply_text(f"Your example device is{user_answers['example_device']}. Now give me a target device:")
    
    return SECOND_QUESTION

    """await update.message.reply_text("Enter example device name:")
    global example_device, target_device
    example_device = update.message.from_user
    print(f"Example device:{example_device}")

    if example_device and target_device != None:
        is_setup_done = True
        await update.message.reply_text("Setup is done")"""
    

async def target_device_name_set (update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_answers["target_device"] = update.message.text
    update.message.reply_text(f"Devices are succesfully saved")
    return ConversationHandler.END
    """await update.message.reply_text("Enter target device name:")
    global example_device, target_device
    target_device = update.message.from_user
    print(f"Target device:{target_device}")


    if example_device and target_device != None:
        is_setup_done = True
        await update.message.reply_text("Setup is done")"""
    


if __name__ == "__main__":
    app = Application.builder().token(token).build()
    print("Starting bot...")


    #Commands
    app.add_handler(CommandHandler("start", start_command)) 
    app.add_handler(CommandHandler("example_set", example_device_name_set))
    app.add_handler(CommandHandler("target_set", target_device_name_set))


    #Polling
    print("Polling...")
    app.run_polling(poll_interval=3)
