import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import time
import logging
from datetime import datetime
from threading import Thread  # Импорт Thread для многопоточности

# Настройка логирования
logging.basicConfig(level=logging.INFO)

TOKEN = '6701431134:AAF1jJ1BwVfE1leAHNYr1N6oQKPB9FYeiXo'
bot = telebot.TeleBot(TOKEN)

subscribed_chats = set()
sent_tasks = []


def fetch_tasks():
    try:
        response = requests.get('https://freelance.habr.com/tasks')
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            tasks = soup.find_all('div', class_='task__title')
            all_tasks_today = [f'{task.text.strip()} | https://freelance.habr.com{task.find("a").get("href")}' for task
                               in tasks]
            return all_tasks_today
        else:
            logging.error(f'Failed to fetch tasks with status code: {response.status_code}')
            return []
    except Exception as ex:
        logging.error(f'Error fetching tasks: {ex}')
        return []


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Используй /subscribe для подписки на уведомления.")


@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    subscribed_chats.add(message.chat.id)
    logging.info(f"Chat {message.chat.id} subscribed.")
    bot.reply_to(message, "Вы подписались на уведомления.")


@bot.message_handler(commands=['unsubscribe'])
def unsubscribe(message):
    if message.chat.id in subscribed_chats:
        subscribed_chats.remove(message.chat.id)
        logging.info(f"Chat {message.chat.id} unsubscribed.")
        bot.reply_to(message, "Вы отписались от уведомлений.")
    else:
        bot.reply_to(message, "Вы не были подписаны на уведомления.")


def check_and_notify():
    while True:
        new_tasks = fetch_tasks()
        if new_tasks:
            unsent_tasks = [task for task in new_tasks if task not in sent_tasks]
            if unsent_tasks:
                logging.info('New tasks found: %s', unsent_tasks)
                for chat_id in subscribed_chats:
                    try:
                        for new_task in unsent_tasks:
                            logging.info(f"Sending task to chat {chat_id}: {new_task}")
                            bot.send_message(chat_id, new_task)
                    except Exception as e:
                        logging.error(f"Failed to send message to chat {chat_id}: {e}")
                sent_tasks.extend(unsent_tasks)

                # Сброс списка отправленных задач каждый день в 00:00
                now = datetime.now()
                if now.hour == 0 and now.minute < 1:  # Проверяем, не прошло ли 1 минута с полуночи
                    sent_tasks.clear()
        time.sleep(300)  # Пауза 5 минут


if __name__ == '__main__':
    bot.remove_webhook()
    Thread(target=lambda: bot.polling(none_stop=True, timeout=60, interval=0)).start()
    check_and_notify()
