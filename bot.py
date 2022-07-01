import telebot
from telebot import types
from config import TOKEN
from whatsapp_parser import *
from selenium.webdriver import Edge
import Youtube_parser
import threading
import ctypes
import csv
import random
import string
import os
import pandas as pd


class InterruptableThread(threading.Thread):
    def __init__(self, target, args=()):
        threading.Thread.__init__(self, target=target, args=args)
        self.target = target
        self.args = args


    def get_id(self):
        if hasattr(self, '_thread_id'):
            return self._thread_id
        for id, thread in threading._active.items():
            if thread is self:
                return id


    def interrupt(self):
        thread_id = self.get_id()
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id,
                                                         ctypes.py_object(SystemExit))
        if res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
            print('Exception raise failure')


class User:
    def __init__(self, id, chat_id, last_message=None, parser=None):
        self.id = id
        self.chat_id = chat_id
        self.last_message = last_message
        self.parser = parser
        self.__current_operation = None
        self.__operation_started = threading.Event()
        self.whatsapp_chatname = ''
        self.youtube_video_url = ''
        self.youtube_phrase = ''
        threading.Thread(target=self.__close_on_inaction).start()


    def start_operation(self, target, args=()):
        # if not (self.__current_operation and self.__current_operation.is_alive()):
        #     self.__operation_started.set()
        #     # self.__current_operation = InterruptableThread(target=self.__wait_for_operation_finished,
        #     #                                                args=(target, args))
        #     self.__current_operation = InterruptableThread(target, args)
        #     self.__current_operation.start()
        InterruptableThread(target=self.__wait_for_operation_finished, args=(target, args)).start()


    def __wait_for_operation_finished(self, target, args=()):
        if self.__current_operation and self.__current_operation.is_alive():
            # дожидаемся завершения последней операции
            self.__current_operation.join()
        self.__current_operation = threading.current_thread()
        self.__operation_started.set()
        target(*args)


    def stop_operation(self):
        if self.__current_operation and self.__current_operation.is_alive():
            self.__current_operation.interrupt()
            return True
        return False


    def __close_on_inaction(self):
        # если парсер длительное время бездействует, закрываем его
        while True:
            is_set = self.__operation_started.wait(180)
            if (not is_set and  # таймаут вышел
                self.parser and  # парсер запущен
                not (self.__current_operation and self.__current_operation.is_alive())):  # а работы не идёт
                self.parser.close()
                self.parser = None
                break
            self.__operation_started.clear()


class Bot:
    # идентификаторы кнопок
    START = 'start'
    WHATSAPP = 'WhatsApp'
    YOUTUBE = 'YouTube'
    CONTACTS_ONE = 'GetContactsFromOne'
    CONTACTS_ALL = 'GetContactsFromAll'
    MESSAGES_ONE = 'GetMessagesFromOne'
    MESSAGES_ALL = 'GetMessagesFromAll'
    BACK = 'Back'


    def __init__(self, token):
        self.__tgbot = telebot.TeleBot(token)
        self.__user_table = []
        print('Бот запущен')

        @self.__tgbot.message_handler(commands=['start'])
        def start(message):
            # заносим пользователя в список, если он ещё не был в него внесён
            if not self.__find_user(message.from_user.id):
                new_user = User(message.from_user.id, message.chat.id, self.START)
                self.__user_table.append(new_user)
                print(f'Пользователь {new_user.id} начал использовать парсер.')
                # предлагаем выбрать парсер
                self.__send_parser_choosing_menu(new_user.chat_id)


        @self.__tgbot.callback_query_handler(func=lambda call: True)
        def buttons_handler(call):
            self.__tgbot.answer_callback_query(call.id)
            user = self.__find_user(call.from_user.id)
            if user:
                markup = types.InlineKeyboardMarkup()
                if call.data == self.START:
                    self.__send_parser_choosing_menu(new_user.chat_id)
                elif call.data == self.WHATSAPP and user.last_message == self.START:
                    user.last_message = self.WHATSAPP
                    # запускаем WhatsApp-парсер
                    markup.add(types.InlineKeyboardButton('Отмена',
                                                             callback_data=self.BACK))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Ожидайте, требуется авторизация в WhatsApp...\n' +
                                                    'Пока откройте мессенджер на своём телефоне',
                                              reply_markup=markup)
                    user.start_operation(self.__start_whatsapp_parsing, (user, ))
                elif call.data == self.BACK:
                    if user.last_message == self.WHATSAPP:
                        user.last_message = self.START
                        # отменяем авторизацию
                        browser_closed = user.stop_operation()
                        if not browser_closed and user.parser:
                            # никаких операций в данный момент не производилось, но браузер запущен
                            user.parser.close()
                        self.__tgbot.send_message(user.chat_id, 'Отмена операции...')
                        # присылаем меню с выбором парсеров
                        self.__send_parser_choosing_menu(user.chat_id)
                    elif user.last_message == self.CONTACTS_ONE or user.last_message == self.MESSAGES_ONE:
                        user.last_message = self.WHATSAPP
                        self.__send_whatsapp_options_menu(user)
                    elif user.last_message == self.CONTACTS_ALL or user.last_message == self.MESSAGES_ALL:
                        user.last_message = self.WHATSAPP
                        user.stop_operation()
                        self.__tgbot.send_message(user.chat_id, 'Отмена операции...')
                        self.__send_whatsapp_options_menu(user)
                    elif user.last_message == self.YOUTUBE:
                        if user.youtube_video_url:
                            user.youtube_video_url = ''
                            markup.add(types.InlineKeyboardButton('Назад',
                                                                  callback_data=self.BACK))
                            self.__tgbot.send_message(user.chat_id,
                                                      text='Пришлите ссылку на видео, в котором будем искать фразу, ' +
                                                           'либо вернитесь в меню выбора действий:',
                                                      reply_markup=markup)
                        elif user.youtube_phrase:
                            user.youtube_phrase = ''
                            markup.add(types.InlineKeyboardButton('Назад',
                                                                  callback_data=self.BACK))
                            self.__tgbot.send_message(user.chat_id,
                                                      text='Введите фразу, которую будем искать, или выберите ' +
                                                           'другое видео:',
                                                      reply_markup=markup)
                elif call.data == self.YOUTUBE and user.last_message == self.START:
                    user.last_message = self.YOUTUBE
                    markup.add(types.InlineKeyboardButton('Назад',
                                                          callback_data=self.BACK))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Пришлите ссылку на видео, в котором будем искать фразу, ' +
                                                   'либо вернитесь в меню выбора действий:',
                                              reply_markup=markup)
                elif call.data == self.CONTACTS_ONE and user.last_message == self.WHATSAPP:
                    if user.parser:
                        user.last_message = self.CONTACTS_ONE
                        markup.add(types.InlineKeyboardButton('Назад',
                                                                 callback_data=self.BACK))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Введите название чата, телефоны ' +
                                                       'из которого вы хотите получить, ' +
                                                       'или вернитесь к меню выбора действий:',
                                                  reply_markup=markup)
                    else:
                        # парсер был выключен из-за длительного бездействия
                        self.__restart(user)
                elif call.data == self.CONTACTS_ALL:
                    if user.parser:
                        markup.add(types.InlineKeyboardButton('Отмена',
                                                              callback_data=self.BACK))
                        user.start_operation(self.__get_contacts_from_all_chats, args=(user,))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Подождите, процесс может занять несколько минут...',
                                                  reply_markup=markup)
                    else:
                        # парсер был выключен из-за длительного бездействия
                        self.__restart(user)
                elif call.data == self.MESSAGES_ONE:
                    if user.parser:
                        user.last_message = self.MESSAGES_ONE
                        markup.add(types.InlineKeyboardButton('Назад',
                                                              callback_data=self.BACK))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Введите название чата, сообщения из которого хотите ' +
                                                       'получить, либо вернитесь назад:',
                                                  reply_markup=markup)
                    else:
                        # парсер был выключен из-за длительного бездействия
                        self.__restart(user)
                elif call.data == self.MESSAGES_ALL:
                    if user.parser:
                        markup.add(types.InlineKeyboardButton('Отмена',
                                                              callback_data=self.BACK))
                        user.start_operation(self.__get_messages_from_all_chats, args=(user,))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Подождите, процесс может занять длительное время...',
                                                  reply_markup=markup)
                    else:
                        # парсер был выключен из-за длительного бездействия
                        self.__restart(user)

        @self.__tgbot.message_handler(content_types=['text'])
        def text_handler(message):
            user = self.__find_user(message.from_user.id)
            if user:
                markup = types.InlineKeyboardMarkup()
                if user.last_message == self.CONTACTS_ONE:
                    user.whatsapp_chatname = message.text
                    markup.add(types.InlineKeyboardButton('Отмена',
                                                          callback_data=self.BACK))
                    user.start_operation(self.__get_contacts_from_chat, args=(user, ))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Подождите, процесс может занять несколько минут...',
                                              reply_markup=markup)
                elif user.last_message == self.MESSAGES_ONE:
                    user.whatsapp_chatname = message.text
                    markup.add(types.InlineKeyboardButton('Отмена',
                                                          callback_data=self.BACK))
                    user.start_operation(self.__get_messages_from_chat, args=(user, ))
                    self.__tgbot.send_message(user.chat_id,
                                              text='Подождите, процесс может занять несколько минут...',
                                              reply_markup=markup)
                elif user.last_message == self.YOUTUBE:
                    if not user.youtube_video_url:
                        # отправлен url видео
                        user.youtube_video_url = message.text
                        markup.add(types.InlineKeyboardButton('Назад',
                                                              callback_data=self.BACK))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Введите фразу, которую будем искать, или выберите ' +
                                                       'другое видео:',
                                                  reply_markup=markup)
                    elif not user.youtube_phrase:
                        # отправлена фраза для поиска в видео
                        user.youtube_phrase = message.text
                        markup.add(types.InlineKeyboardButton('Отмена',
                                                              callback_data=self.BACK))
                        self.__tgbot.send_message(user.chat_id,
                                                  text='Подождите, процесс может занять несколько минут...',
                                                  reply_markup=markup)
                        user.start_operation(target=self.__parse_youtube, args=(user, ))
        self.__tgbot.polling(none_stop=True)


    def __get_contacts_from_chat(self, user):
        try:
            result = user.parser.parse_dialog(name=user.whatsapp_chatname, get_messages=False)
            if not result:
                self.__tgbot.send_message(user.chat_id,
                                          text='К сожалению, ничего не нашлось.')
            else:
                filename = self.__prepare_whatsapp_csv(result, write_messages=True, user_id=user.id)
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    self.__tgbot.send_document(user.chat_id, f, caption='Вот что удалось найти')
                os.remove(filename)
        finally:
            user.whatsapp_chatname = ''
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Назад',
                                                  callback_data=self.BACK))
            self.__tgbot.send_message(user.chat_id,
                                      text='Введите название чата, телефоны ' +
                                           'из которого вы хотите получить, ' +
                                           'или вернитесь к меню выбора действий:',
                                      reply_markup=markup)
            user.last_message = self.CONTACTS_ONE


    def __get_contacts_from_all_chats(self, user):
        try:
            result = user.parser.parse_dialog(get_messages=False)
            if not result:
                self.__tgbot.send_message(user.chat_id,
                                          text='К сожалению, ничего не нашлось.')
            else:
                filename = self.__prepare_whatsapp_csv(result, write_messages=False, user_id=user.id)
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    self.__tgbot.send_document(user.chat_id, f, caption='Вот что удалось найти')
                os.remove(filename)
        finally:
            self.__send_whatsapp_options_menu(user)


    def __get_messages_from_chat(self, user):
        try:
            result = user.parser.parse_dialog(name=user.whatsapp_chatname, get_messages=True)
            if not result:
                self.__tgbot.send_message(user.chat_id,
                                          text='К сожалению, ничего не нашлось.')
            else:
                filename = self.__prepare_whatsapp_csv(result, write_messages=True, user_id=user.id)
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    self.__tgbot.send_document(user.chat_id, f, caption='Вот что удалось найти')
                os.remove(filename)
        finally:
            user.whatsapp_chatname = ''
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Назад',
                                                  callback_data=self.BACK))
            self.__tgbot.send_message(user.chat_id,
                                      text='Введите название чата, сообщения из которого хотите ' +
                                           'получить, либо вернитесь назад:',
                                      reply_markup=markup)
            user.last_message = self.MESSAGES_ONE



    def __get_messages_from_all_chats(self, user):
        try:
            result = user.parser.parse_dialog(get_messages=True)
            if not result:
                self.__tgbot.send_message(user.chat_id,
                                          text='К сожалению, ничего не нашлось.')
            else:
                filename = self.__prepare_whatsapp_csv(result, write_messages=True, user_id=user.id)
                with open(filename, 'r', newline='', encoding='utf-8') as f:
                    self.__tgbot.send_document(user.chat_id, f, caption='Вот что удалось найти')
                os.remove(filename)
        finally:
            self.__send_whatsapp_options_menu(user)


    def __prepare_whatsapp_csv(self, parsing_result, write_messages, user_id):
        csv_list = []
        filename = str(user_id) + '.csv'
        if write_messages:
            csv_list.append(['Название чата', 'Время', 'Отправитель', 'Сообщение'])
            for dlg_info in parsing_result:
                for date_time, sender, text in dlg_info.messages:
                    csv_list.append([dlg_info.name, date_time, sender, text])
            dataframe = pd.DataFrame({
                'Название чата': [el[0] for el in csv_list],
                'Время': [el[1] for el in csv_list],
                'Отправитель': [el[2] for el in csv_list],
                'Сообщение': [el[3] for el in csv_list]
            })
        else:
            for dlg_info in parsing_result:
                for number in dlg_info.numbers:
                    csv_list.append([dlg_info.name, number])
            dataframe = pd.DataFrame({
                'Название чата': [el[0] for el in csv_list],
                'Телефон': [el[1] for el in csv_list]
            })

        dataframe.to_csv(filename, index=False, encoding='utf-8', sep = ';')
        return filename


    def __parse_youtube(self, user):
        try:
            result = Youtube_parser.main(user.youtube_video_url, user.youtube_phrase)
            self.__tgbot.send_mesage(user.chat_id, result)
        finally:
            user.youtube_phrase = ''
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton('Назад',
                                                  callback_data=self.BACK))
            self.__tgbot.send_message(user.chat_id,
                                      text='Введите фразу, которую будем искать, или выберите ' +
                                           'другое видео:',
                                      reply_markup=markup)


    def __restart(self, user):
        next_menu.add(types.InlineKeyboardButton('Старт',
                                                 callback_data=self.START))
        self.__tgbot.send_message(user.chat_id,
                                  text='Время ожидания истекло! Нажмите "Старт", чтобы начать снова:',
                                  reply_markup=next_menu)
        user.last_message = self.START


    def __send_parser_choosing_menu(self, chat_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Парсинг WhatsApp',
                                              callback_data=self.WHATSAPP))
        markup.add(types.InlineKeyboardButton('Парсинг YouTube',
                                              callback_data=self.YOUTUBE))
        self.__tgbot.send_message(chat_id,
                                  text='Выберите действие:',
                                  reply_markup=markup)


    def __send_whatsapp_options_menu(self, user):
        markup = types.InlineKeyboardMarkup()

        markup.add(types.InlineKeyboardButton('Получить список телефонов из чата',
                                              callback_data=self.CONTACTS_ONE))
        markup.add(types.InlineKeyboardButton('Получить список телефонов из всех чатов',
                                              callback_data=self.CONTACTS_ALL))
        markup.add(types.InlineKeyboardButton('Получить сообщения из чата',
                                              callback_data=self.MESSAGES_ONE))
        markup.add(types.InlineKeyboardButton('Получить сообщения из всех чатов',
                                              callback_data=self.MESSAGES_ALL))
        markup.add(types.InlineKeyboardButton('Назад',
                                              callback_data=self.BACK))
        self.__tgbot.send_message(user.chat_id,
                                  text='Что вы хотите сделать?',
                                  reply_markup=markup)


    def __start_whatsapp_parsing(self, user):
        try:
            user.parser = WhatsAppParser(hidden=True)
            t1 = threading.Thread(target=self.__authorize_user, args=(user, ))
            t1.start()
            user.parser.open()
            t1.join()
        except SystemExit:
            # пользователь прервал операцию
            print()
            user.parser.close()


    def __authorize_user(self, user):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Назад',
                                              callback_data=self.BACK))
        try_num, limit = 0, 10
        while True:
            # ждём появления или изменения скриншота с qr-кодом
            is_set = user.parser.screenshot_changed.wait(180)
            if not is_set:
                # время ожидания истекло
                break
            user.parser.screenshot_changed.clear()
            if user.parser.screenshot:
                # qr-код изменился
                self.__tgbot.send_photo(user.chat_id,
                                        photo=user.parser.screenshot,
                                        caption='Пожалуйста, проследуйте инструкции на скриншоте.\n' +
                                        'Боту необходим временный доступ к вашим чатам.\n' +
                                        'QR-код актуален не более одной минуты. При его изменении вам будет ' +
                                        'отправлена его обновлённая версия.',
                                        reply_markup=markup)
                try_num += 1
                if try_num >= limit:
                    # если пользователь забросил бота, нужно перестать выполнять эту операцию
                    break
            else:
                # авторизация завершена
                self.__send_whatsapp_options_menu(user)
                break


    def __find_user(self, user_id):
        return next((user for user in self.__user_table if user_id == user.id), None)


Bot(TOKEN)
