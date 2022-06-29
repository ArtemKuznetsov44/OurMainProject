import telebot  # pip install pyTelegramBotAPI
from telebot import types
from config import TOKEN
from main import WhatsAppParser
from selenium.webdriver import Edge


class Bot:
    def __init__(self, token):
        """Создаёт Telegram-бота с указанным токеном и сценарием.

        Параметры:
        token - токен бота
        """
        self.token = token
        self.tgbot = telebot.TeleBot(token)
        self.mode_switch = 'None'

        @self.tgbot.message_handler(commands=['start'])
        def start(message):
            # Создаем две начальный выбор
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('WhatAppParser',
                                                  callback_data='WhatApp'))
            markup.add(types.InlineKeyboardButton('YoutubeParser',
                                                  callback_data='Youtube'))
            self.tgbot.send_message(message.chat.id, text="Заглушка",
                                    reply_markup=markup)

        @self.tgbot.callback_query_handler(func=lambda call: True)
        def choose_parser(call):
            self.tgbot.answer_callback_query(call.id)
            next_menu = types.InlineKeyboardMarkup()
            # Создаем
            if call.data == 'WhatApp':
                next_menu.add(types.InlineKeyboardButton('Получение Имени и Телефона пользователя',
                                                         callback_data='GetContact'))
                next_menu.add(types.InlineKeyboardButton('Получения всех телефонов пользователей из групповых чатов',
                                                         callback_data='GetGroup'))
                next_menu.add(types.InlineKeyboardButton('Получение всех сообщений от одного пользователя',
                                                         callback_data='GetMessageFromContact'))
                next_menu.add(types.InlineKeyboardButton('Получение всех сообщений из группового Чата',
                                                         callback_data='GetMessageFromGroup'))
                next_menu.add(types.InlineKeyboardButton('Назад',
                                                         callback_data='Back'))
                self.tgbot.send_message(call.message.chat.id,
                                        text="Заглушка",
                                        reply_markup=next_menu)
            elif call.data == 'Back':
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton('WhatAppParser',
                                                      callback_data='WhatApp'))
                markup.add(types.InlineKeyboardButton('YoutubeParser',
                                                      callback_data='Youtube'))
                self.tgbot.send_message(call.message.chat.id,
                                        text="Заглушка",
                                        reply_markup=markup)
            elif call.data == 'Youtube':
                next_menu.add(types.InlineKeyboardButton('Вернутся в начало',
                                                         callback_data='Back'))
                self.tgbot.send_message(call.message.chat.id,
                                        text="Пожалуйста введите название видеоролика который вы хотите найти",
                                        reply_markup=next_menu)
            elif call.data == 'GetContact' or call.data == 'GetMessageFromContact':
                next_menu.add(types.InlineKeyboardButton('Вернутся в начало',
                                                         callback_data='Back'))
                self.tgbot.send_message(call.message.chat.id,
                                        text="Пожалуйста введите название контакта который вы хотите найти",
                                        reply_markup=next_menu)
            elif call.data == 'GetGroup' or call.data == 'GetMessageFromGroup':
                next_menu.add(types.InlineKeyboardButton('Вернутся в начало',
                                                         callback_data='Back'))
                self.tgbot.send_message(call.message.chat.id,
                                        text="Пожалуйста введите название группового чата который вы хотите найти",
                                        reply_markup=next_menu)
            self.mode_switch = call.data
            # TODO Сделать создание кнопок выбора операции для ютуба
            # TODO Реализовать методы для кнопок WhatApp_Parser и YouTube_Parser

        @self.tgbot.message_handler(content_types=['text'])
        def multifunctional_method(message):
            if self.mode_switch == 'GetContact':
                driver = Edge()
                get_name_and_number(driver, message)
            elif self.mode_switch == 'GetGroup':
                driver = Edge()
                get_name_and_number(driver, message)
            # elif self.mode_switch == 'GetMessageFromContact':
            #
            # elif self.mode_switch=='GetMessageFromGroup':
            # elif self.mode_switch == 'Youtube':
            else:
                self.tgbot.send_message(message.chat.id,
                                        text="Но вы же еще не выбрали что вы будете делать!")

        def get_name_and_number(driver, message):
            with WhatsAppParser(driver) as parser:
                names_phones = parser.parse_dialog(message.text)
                for name, phone in names_phones:
                    print('Имя:', name)
                    print('Телефон:', phone)
                    print('=' * 50)

        self.tgbot.polling(none_stop=True)


Bot(TOKEN)
