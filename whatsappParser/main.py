from selenium.webdriver import Edge
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as BS
from time import sleep
import datetime as dt
# from tqdm import tqdm

import webbrowser

# открываем WhatsApp в браузере
driver = Edge()
driver.get("https://web.whatsapp.com")

def find_element_or_none(parent, by, value):
    try:
        return parent.find_element(by=by, value=value)
    except NoSuchElementException:
        return None

def find_elements_or_none(parent, by, value):
    try:
        return parent.find_elements(by=by, value=value)
    except NoSuchElementException:
        return None

try:
    # ждём появления qr-кода
    wait(driver, 30).until(
        EC.presence_of_element_located((By.XPATH,
                                        '//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/canvas'))
    )
    token = find_element_or_none(parent=driver,
                                 by=By.XPATH,
                                 value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div').get_attribute('data-ref')
    screenshot = driver.save_screenshot('my_screenshot.png')
    while True:
        # TODO: поставить таймаут
        sleep(10)
        button = find_element_or_none(parent=driver,
                                      by=By.XPATH,
                                      value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div/span/button')
        if button:
            # перегенерируем qr-код
            sleep(1)
            button.click()
            sleep(1)
        new_token_web_el = find_element_or_none(parent=driver,
                                         by=By.XPATH,
                                         value='//*[@id="app"]/div/div/div[2]/div[1]/div/div[2]/div')
        if not new_token_web_el:
            # токен пропал - страница поменялась
            break
        new_token = new_token_web_el.get_attribute('data-ref')
        if new_token != token:
            token = new_token
            screenshot = driver.save_screenshot('my_screenshot.png')
            print('QR изменился')
    # ожидаем, когда прогрузится страница с диалогами
    wait(driver, 600).until(
        EC.presence_of_element_located((By.XPATH,
                                        '//*[@id="pane-side"]/div/div/div'))
    )
    sleep(3)  # TODO: дожидаться пока диалоги прогрузятся полностью
    # pane_side = driver.find_element(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div')

    # подгружаем диалоги
    dialogs = driver.find_elements(by=By.XPATH, value='//*[@id="pane-side"]/div/div/div/div')
    # TODO: что делать если нет диалогов

    # print(len(dialogs))

    # dialog.click()

    # divs = pane_side.find_elements_by_tag_name('div')
    # print(len(divs))

    # html = pane_side.get_attribute('innerHTML')
    names_phones = []
    dates_messages = []
    result = []
    # for dlg in dialogs:
    # with open('index.html', 'a', encoding='utf-8') as f:
    # f.write(dlg.get_attribute('innerHTML')
    for dlg in dialogs:
        # заходим в диалог
        dlg.click()
        # ищем информацию о номере телефона
        # открываем информацию о профиле собеседника
        profile = find_element_or_none(parent=driver,
                                       by=By.XPATH,
                                       value='//*[@id="main"]/header/div[2]/div/div/span')
        profile.click()
        sleep(3)  # TODO: дожидаться прогрузки
        name = find_element_or_none(parent=driver,
                                    by=By.XPATH,
                                    value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/h2/span').text
        phone = find_element_or_none(parent=driver,
                                     by=By.XPATH,
                                     value='//*[@id="app"]/div/div/div[2]/div[3]/span/div/span/div/div/section/div[1]/div[2]/div/span/span').text
        names_phones.append((name, phone))
        # скроллим диалог до начала
        find_element_or_none(parent=driver,
                             by=By.XPATH,
                             value='//*[@id="main"]/div[3]/div/div[2]').send_keys(Keys.CONTROL + Keys.HOME)
        # собираем сообщения и их даты
        list_items = find_elements_or_none(parent=driver,
                                           by=By.CLASS_NAME,
                                           value='focusable-list-item')
        # messages = []
        # for md in messages_and_dates:
        #     # убираем из найденных элементов те, которые не являются
        #     # входящими или исходящими сообщениями
        #     classes = md.get_attribute('class').split()
        #     if 'message-out' in classes or 'message-in' in classes:
        #         messages.append(md)
        for i, item in enumerate(list_items):
            # TODO: сегодня и вчера заменить на даты
            datetime_sender_web_el = find_element_or_none(parent=item,
                                                          by=By.CLASS_NAME,
                                                          value='copyable-text')
            if datetime_sender_web_el:
                # для сообщений типа "текст", "контакт"
                datetime_sender = datetime_sender_web_el.get_attribute('data-pre-plain-text')
                date_time = datetime_sender[1:18]
                sender = datetime_sender[20:-2]
                text_web_el = find_element_or_none(parent=item,
                                                   by=By.CLASS_NAME,
                                                   value='selectable-text')
                text_web_el = find_element_or_none(parent=text_web_el,
                                                   by=By.TAG_NAME,
                                                   value='span')
                text = text_web_el.text if text_web_el else ''
            else:
                # для сообщений типа "фото", "видео", "документ"
                # видео: .//div[3]/div/div[1]/div[1]/div/div[2]/div/span
                # фото: .//div[2]/div/div[1]/div[1]/div/div[2]/div/span
                # док: .//div[2]/div/div[1]/div[1]/div[2]/div/span
                time_web_el = find_element_or_none(parent=item,
                                                   by=By.XPATH,
                                                   value='.//div/div[1]/div[1]/div/div[2]/div/span')
                if time_web_el:
                    time = time_web_el.text  # TODO: время последнего видео
                    text = '[фото/видео]'  # TODO: различать фото и видео
                else:
                    time_web_el = find_element_or_none(parent=item,
                                                       by=By.XPATH,
                                                       value='.//div/div[1]/div[1]/div[2]/div/span')
                    if time_web_el:
                        time = time_web_el.text
                        text = '[документ]'  # TODO: название документа
                    else:
                        # плашка с датой
                        continue
                for item_reversed in list_items[i::-1]:
                    # ищём дату сообщения
                    date_web_el = find_element_or_none(parent=item_reversed,
                                                       by=By.XPATH,
                                                       value='.//div/span')
                    if date_web_el:
                        date = date_web_el.text
                        if date == 'ВЧЕРА':
                            date = dt.date.today() - dt.timedelta(days=1)
                            date = date.strftime('%d.%m.%Y')
                        elif date == 'СЕГОДНЯ':
                            date = dt.date.today().strftime('%d.%m.%Y')
                        # TODO: дни недели
                date_time = f'{time}, {date}'
                sender = 'ну кто-то'  # TODO: кто
            result.append((date_time, sender, text))  # TODO: классы вместо кортежей
        sleep(3)
    # webbrowser.open('index.html', new=2)
finally:
    print('Имена и номера:', names_phones)
    for date_time, sender, text in result:
        print('='*30)
        print('Дата:', date_time)
        print('От:', sender)
        print('Сообщение:', text)
    driver.quit()
