from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementNotInteractableException, TimeoutException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from time import sleep
import datetime as dt
# from tqdm import tqdm
import re
import webbrowser
from multiprocessing import Process, Condition


class WhatsAppParser:
    def __init__(self):
        self.__driver = Edge()
        self.screenshot_taken = Condition()


    def __enter__(self):
        # открываем WhatsApp в браузере
        self.__driver.get('https://web.whatsapp.com')  # TODO: сделать браузер невидимым

        # сохраняем qr-коды
        self.__take_qr_screenshots()  # TODO: событие появления нового скриншота

        # ожидаем, когда прогрузится страница с диалогами, и находим строку поиска
        # wait(self.__driver, 60).until(EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div')))
        # self.searchbar = self.__find_element_or_none('//*[@id="side"]/div[1]/div/div/div[2]/div/div[2]')
        self.searchbar = wait(self.__driver, 60).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="side"]/div[1]/div/div/div[2]/div/div[2]'))
        )
        sleep(5)  # даём прогрузиться диалогам
        '//*[@id="side"]/div[1]/div/div/div[2]/div/div[2]'

        return self


    def __exit__(self, exc_type, exc_val, exc_tb):
        # выходим из аккаунта
        self.__log_out()
        # закрываем браузер
        self.__driver.quit()


    def __try_to_click(self, web_el, timeout=10):
        clicked = False
        last_exception = None
        i = 0
        sleep(0.5)
        while not clicked and i < timeout:
            try:
                web_el.click()
                clicked = True
            except Exception as ex:
                last_exception = ex
                sleep(1)
                i += 1
        if not clicked:
            raise last_exception


    def __try_to_send_keys(self, web_el, keys, timeout=10):
        done = False
        last_exception = None
        i = 0
        while not done and i < timeout:
            try:
                web_el.send_keys(keys)
                done = True
            except Exception as ex:
                last_exception = ex
                sleep(1)
                i += 1
        if not done:
            raise last_exception


    def __log_out(self):
        # ищем и открываем меню
        menu_web_el = self.__find_element_or_none('//*[@id="side"]/header/div[2]/div/span/div[3]/div/span')
        self.__try_to_click(menu_web_el)

        # ждём и кликаем по кнопке "Выход"
        quit_menu = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="side"]/header/div[2]/div/span/div[3]/span/div/ul'))
        )
        quit_btn = self.__find_elements_or_none(parent=quit_menu, value='.//li')[-1]
        self.__try_to_click(quit_btn)

        # подтверждаем выход
        sure_quit = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="app"]/div/span[2]/div/div/div/div/div/div/div[3]/div/div[2]'))
        )
        self.__try_to_click(sure_quit)

        # дожидаемся окончания выхода - ждём появления страницы с входом
        wait(self.__driver, 30).until(
            EC.presence_of_element_located((By.XPATH,
                                            '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/canvas'))
        )


    def __verify_contact_name(self, dialog_web_el):
        dialog_name = self.__find_element_or_none(parent=dialog_web_el,
                                                  value='.//div/div/div[2]/div[1]/div[1]/span').text
        if re.match(r'\+\d{1} \d{3} \d{3}-\d{2}-\d{2}', dialog_name):
            sleep(2)  # TODO: посмотреть что можно сделать с задержкой
            dialog_name = self.__find_element_or_none(parent=dialog_web_el,
                                                      value='.//div/div/div[2]/div[1]/div[1]/span').text
        return dialog_name


    def parse_dialog(self, name=None, get_messages=True):
        # ищем диалог с указанным именем
        if name:
            # self.searchbar.send_keys(name)
            self.__try_to_send_keys(self.searchbar, name)
            sleep(2)
            found_chats = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div/div/div'))
            )
        else:
            self.searchbar.click()
            found_chats = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="pane-side"]/div[1]/div/div'))
            )

        result = []


        if found_chats:
            # диалоги с подходящими названиями найдены
            last_dlg = self.searchbar
            zero = self.__find_element_or_none(parent=self.searchbar, value='..')
            dialog_idx = 0
            while True:
                # листаем список найденных диалогов
                # last_dlg.send_keys(Keys.DOWN)
                # try:
                #     self.__try_to_send_keys(last_dlg, Keys.DOWN)
                # except:
                #     break
                self.searchbar.click()
                for i in range(dialog_idx + 2):
                    self.__try_to_send_keys(self.__driver.switch_to.active_element, Keys.DOWN)
                sleep(1)
                current_dlg = self.__find_element_or_none(parent=self.__driver.switch_to.active_element,
                                                          value='..')
                if current_dlg == last_dlg:
                    # мы нажали на стрелочку вниз, но список диалогов не пролистался, - 
                    # значит, мы дошли до его конца
                    break
                else:
                    last_dlg = current_dlg
                    dialog_idx += 1
                # ищем элемент с датой последнего сообщения
                # last_mes_date = self.__find_element_or_none(parent=current_dlg,
                #                                             value='.//div/div/div[2]/div[1]/div[2]')
                try:
                    last_mes_date = wait(current_dlg, 5).until(
                        EC.presence_of_element_located((By.XPATH, './/div/div/div[2]/div[1]/div[2]'))
                    )
                except TimeoutException:
                    last_mes_date = None
                if not last_mes_date:
                    # диалог ещё не был начат - мы дошли до списка контактов
                    break
                if get_messages:
                    messages = self.__get_messages()
                    result.append(messages)
                    current_dlg.click()
                else:
                    name_phones = self.__get_name_and_number()
                    result.append(name_phones)
                self.__try_to_click(found_chats)
        return result


    DAYS_OF_WEEK = ['ПОНЕДЕЛЬНИК', 'ВТОРНИК', 'СРЕДА', 'ЧЕТВЕРГ', 'ПЯТНИЦА', 'СУББОТА', 'ВОСКРЕСЕНЬЕ']
    def __get_date_by_weekday(self, weekday):
        current_day = dt.datetime.today().isoweekday()
        delta = current_day - (self.DAYS_OF_WEEK.index(weekday)+1)
        if delta < 0:
            delta += 7
        return (dt.date.today() - dt.timedelta(days=delta)).strftime('%d.%m.%Y')


    def __find_element_or_none(self, value, parent=None, by=None):
        if parent is None:
            parent = self.__driver
        if by is None:
            by = By.XPATH
        try:
            return parent.find_element(by=by, value=value)
        except NoSuchElementException:
            return None


    def __find_elements_or_none(self, value, parent=None, by=None):
        if parent is None:
            parent = self.__driver
        if by is None:
            by = By.XPATH
        try:
            return parent.find_elements(by=by, value=value)
        except NoSuchElementException:
            return None


    def __take_qr_screenshots(self):
        # ждём появления qr-кода
        wait(self.__driver, 30).until(
            EC.presence_of_element_located((By.XPATH,
                                            '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/canvas'))
        )
        # screenshot = self.driver.save_screenshot('my_screenshot.png')
        token = None
        while True:
            button = self.__find_element_or_none('//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/span/button')
            if button:
                # перегенерируем qr-код
                sleep(1)
                self.__try_to_click(button)
            try:
                new_token = wait(self.__driver, 3).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div'))
                ).get_attribute('data-ref')
            except:
                # токен пропал - страница поменялась
                break
            if new_token != token:
                # qr-код поменялся
                token = new_token
                # делаем скриншот и уведомляем о его изменении
                self.screenshot = self.__driver.get_screenshot_as_png()
                try:
                    self.screenshot_taken.notify()
                except:
                    # некого уведомлять
                    pass
                print('QR изменился')
            sleep(10)


    def __get_name_and_number(self):
        # ищем информацию о номере телефона
        # открываем информацию о профиле собеседника
        # profile = self.__find_element_or_none('//*[@id="main"]/header/div[2]')
        profile = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/header/div[2]'))
        )
        self.__try_to_click(profile)
        # ждём прогрузки элемента с именем пользователя
        name_web_el = wait(self.__driver, 3).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/h2/span'))
        )
        # TODO: бизнес-аккаунт
        phones = []
        if name_web_el:
            # парсим диалог
            name = name_web_el.text
            phone = self.__find_element_or_none('//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/div/span/span').text
            phones.append(phone)
        else:
            name_web_el = self.__find_element_or_none('//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div/div[2]/div/div[1]/div/div/div[2]')
            if name_web_el:
                # парсим групповой чат
                name = name_web_el.text
                phones_raw = self.__find_element_or_none('//*[@id="main"]/header/div[2]/div[2]/span').text
                phones = phones_raw.split(', ')
            else:
                name_web_el = self.__find_element_or_none('//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[3]/div[1]/div[1]/span')
                if name_web_el:
                    # парсим бизнес-аккаунт
                    name = name_web_el.text
                    phone = self.__find_element_or_none(parent=name_web_el, value='..//..//div[2]/span').text
                    phones.append(phone)
                else:
                    name = '[Чат неизвестного типа]'
                    phones.append('')
        return (name, phones)


    def __get_messages(self):
        # скроллим диалог до начала
        messages_list = wait(self.__driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div[3]/div/div[2]')))
        # TODO: не хватает
        i, limit = 0, 10  # счётчики для отслеживания конца скролла
        while True:
            scroll_top = self.__driver.execute_script('return arguments[0].scrollTop', messages_list)
            if scroll_top == 0:
                i += 1
            else:
                i = 0
            if i == limit:
                # дошли до начала диалога
                # TODO: оптимизировать, особенно для коротких диалогов
                break
            # messages_list.send_keys(Keys.CONTROL + Keys.HOME)
            self.__try_to_send_keys(messages_list, Keys.CONTROL + Keys.HOME)
            sleep(1)
        # собираем сообщения и их даты
        list_items = self.__find_elements_or_none(by=By.CLASS_NAME, value='focusable-list-item')
        messages = []
        for i, item in enumerate(list_items):
            # ищем элемент, содержащий дату и отправителя
            datetime_sender_web_el = self.__find_element_or_none(parent=item,
                                                                 by=By.CLASS_NAME,
                                                                 value='copyable-text')
            try:
                if datetime_sender_web_el:
                    # для сообщений типа "текст", "контакт"
                    mes_info = self.__extract_info_from_text_message(datetime_sender_web_el)
                else:
                    # для сообщений типа "фото", "видео", "документ" и др.
                    mes_info = self.__extract_info_from_media_message(i, list_items)
            except:
                continue
            if mes_info:
                messages.append(mes_info)
        return messages


    def __extract_info_from_text_message(self, datetime_sender_web_el):
        datetime_sender = datetime_sender_web_el.get_attribute('data-pre-plain-text')
        date_time = datetime_sender[1:18]
        sender = datetime_sender[20:-2]
        text_web_el = self.__find_element_or_none(parent=datetime_sender_web_el, by=By.CLASS_NAME, value='selectable-text')
        text_web_el = self.__find_element_or_none(parent=text_web_el, by=By.TAG_NAME, value='span')
        text = text_web_el.text if text_web_el else '[контакт]'
        return (date_time, sender, text)


    def __extract_info_from_media_message(self, i, list_items):
        item = list_items[i]
        # ищем элемент со временем отправки
        time_web_el = self.__find_element_or_none(parent=item,
                                                  value='.//div/div[1]/div[1]/div/div[2]/div/span')
        if time_web_el:
            # фото или видео
            time = time_web_el.text  # TODO: время последнего видео
            text = '[фото/видео]'
        else:
            time_web_el = self.__find_element_or_none(parent=item,
                                                      value='.//div/div[1]/div[1]/div[2]/div/span')
            if time_web_el:
                # документ
                time = time_web_el.text
                text = '[документ]'
            else:
                forwarded_mark = self.__find_element_or_none(parent=item,
                                                            value='.//div/div[1]/div[1]/div[1]/span[2]')
                if forwarded_mark:
                    # пересланное сообщение
                    time = self.__find_element_or_none(parent=item,
                                                       value='.//div/div[1]/div[1]/div[3]/div/span'
                    ).text
                    text = '[пересланное сообщение]'
                else:
                    time_web_el = self.__find_element_or_none(parent=item,
                                                       value='.//div/div[1]/div[1]/div/div[4]/div/span')
                    if time_web_el:
                        # пересланное фото
                        time = time_web_el.text
                        text = '[фото]'
                    else:
                        # неинформативный вспомогательный элемент, например плашка с датой
                        return None
        for item_reversed in list_items[i::-1]:
            # ищём дату сообщения
            date_web_el = self.__find_element_or_none(parent=item_reversed,
                                                      value='.//div/span')
            if date_web_el:
                date = date_web_el.text.upper()
                if date == 'ВЧЕРА':
                    date = dt.date.today() - dt.timedelta(days=1)
                    date = date.strftime('%d.%m.%Y')
                elif date == 'СЕГОДНЯ':
                    date = dt.date.today().strftime('%d.%m.%Y')
                elif date in self.DAYS_OF_WEEK:
                    date = self.__get_date_by_weekday(date)
                elif not re.match(r'([\d]{2}.[\d]{2}.[\d]{4})', date):
                    continue
            if not re.match(r'\d{2}.\d{2}.\d{4}', date):
                # в дате лежит что-то не то
                temp = self.__find_element_or_none('//*[@id="main"]/div[3]/div/div[2]')
                while True:
                    self.__try_to_send_keys(temp, Keys.DOWN)
                    sleep(1)
                    # date = wait(self.__driver, 10).until(
                    #         EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div[3]/div/span/div/div/div/span'))
                    # ).text
                    date_web_el = self.__find_element_or_none('//*[@id="main"]/div[3]/div/span/div/div/div/span')
                    if date_web_el:
                        date = date_web_el.text
                        if date == 'ВЧЕРА':
                            date = dt.date.today() - dt.timedelta(days=1)
                            date = date.strftime('%d.%m.%Y')
                        elif date == 'СЕГОДНЯ':
                            date = dt.date.today().strftime('%d.%m.%Y')
                        elif date in self.DAYS_OF_WEEK:
                            date = self.__get_date_by_weekday(date)
                        break
            else:
                break
        date_time = f'{time}, {date}'
        sender = 'ну кто-то'  # TODO: кто
        return (date_time, sender, text)


with WhatsAppParser() as parser:
    # names_phones = parser.parse_dialog('Выпускники 1989')
    # messages = parser.parse_dialog('Выпускники 1989')  # TODO: диалог только с указанным названием
    messages = parser.parse_dialog('Рпер')
    # TODO: одинаковый выходной результат
    for message in messages:
        for date_time, sender, text in message:
            print('='*50)
            print('Дата:', date_time)
            print('От:', sender)
            print('Сообщение:', text)
        print('~'*80)
    # result = parser.parse_dialog(get_messages=False)
    # for name, phone in result:
    #     print('='*50)
    #     print('Имя:', name)
    #     print('Телефон:', phone)
