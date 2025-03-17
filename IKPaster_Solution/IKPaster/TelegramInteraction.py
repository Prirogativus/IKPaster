import telebot
from telebot import types

TOKEN = ''
bot = telebot.TeleBot(TOKEN)

# Глобальные переменные для хранения моделей
example_model = None
target_model = None

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "Hi! I am your automatization bot.")
    ask_example_model(message.chat.id)

# Функция для запроса примера модели
def ask_example_model(chat_id):
    msg = bot.send_message(chat_id, "Give me an example model:")
    bot.register_next_step_handler(msg, process_example_model_step)

# Обработка ответа о примере модели
def process_example_model_step(message):
    global example_model
    example_model = message.text
    
    # Задаем второй вопрос
    msg = bot.send_message(message.chat.id, "Give me a target model:")
    bot.register_next_step_handler(msg, process_target_model_step)

# Обработка ответа о целевой модели
def process_target_model_step(message):
    global target_model
    target_model = message.text
    
    # Благодарим за ответы
    response = f"Example: {example_model}, Target: {target_model}."
    bot.send_message(message.chat.id, response)
    print(example_model, target_model)

# Команда для получения сохраненных моделей
@bot.message_handler(commands=['show_models'])
def show_models(message):
    if example_model and target_model:
        response = f"Saved models:\nExample: {example_model}\nTarget: {target_model}"
    else:
        response = "No models saved yet. Please use /start command first."
    bot.send_message(message.chat.id, response)

# Запускаем бота
if __name__ == '__main__':
    bot.polling(none_stop=True)
    