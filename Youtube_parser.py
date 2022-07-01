import pandas as pd
import time
import os
from selenium import webdriver


# метод, для открытие драйвера на переданной странице:
def open_url_in_edge(url) -> webdriver:
    options = webdriver.EdgeOptions() # создание драйвера с опциями

    # создание некоторых опций для дравера:
    options.add_argument('--headless') # добавление аргумента открытия браузера в фоновом режиме
    options.add_argument("--mute-audio") # добавление аргумента для бесшумного открытия

    driver = webdriver.Edge('msedgedriver.exe', options=options)  # создание драйвера с опциями

    driver.get(url) # передача ссылки в драйвер
    return driver   # возвращаем драйвер


# метод, для полученния текстовый данных с временем и текстом:
def get_transcript(driver: webdriver) -> str:
    driver.implicitly_wait(10) # неявное ожидание с длительностью

    try: # пытаемся кликнуть на кнопку "..."
        driver.find_elements_by_xpath("//button[@aria-label='More actions']")[1].click()
    except: # если произошла ошибка:
        time.sleep(5) # небольшая задержка
        driver.refresh() # обновление страницы драйвера/браузера
        get_transcript(driver) # повторный вызов метода после обновления содержимого страницы

    try: # пытаемся кликнуть на кноку "показать текст видео"
        res = driver.find_element_by_xpath("//*[@id='items']/ytd-menu-service-item-renderer/tp-yt-paper-item").click()

    except : # если произошла ошибка:
        time.sleep(5) # небольшая задержка
        driver.refresh() # обновление содержимого страницы
        get_transcript(driver) # повторный вызов метода после обновления содержимого страницы

    # начинаем получать данные:
    print(">>> Start transcripting <<<")
    return driver.find_element_by_xpath("//*[@id='body']/ytd-transcript-segment-list-renderer").text # возвращаем полученный текст


# метод для формирования словаря:
def make_dictionary(r_text: str) -> dict:
    time_text_list = r_text.split("\n")

    times = time_text_list[::2] # достаем временные промежутки
    text = time_text_list[1::2] # достаем текст

    return dict(zip(times, text))


# метод для поиска совпадений с переданным тестом:
def find_some_text(our_dict: dict, insert_text: str) -> str:
    insert_text = insert_text.strip() # удаление пробелов в начале в конце строки

    tmp_time_list = []
    for key in our_dict:
        if insert_text in our_dict[key]: tmp_time_list.append(key)

    if len(tmp_time_list) != 0:
        return f"Мы нашли совпадения в данных временных промежутках: {tmp_time_list}"
    # f"Mathes were found on: {[value for value in tmp_time_list]}"
    return "Mathes wrere not found on... Might be worth a look in another video?"


# метод для записи данных в .csv файл:
def write_to_csv_file(our_dict: dict, path: str):
    # перевод данных в формат DataFrae пригодный, для конвертации в .csv:
    dataframe = pd.DataFrame({'time': our_dict.keys(), 'text': our_dict.values()})
    dataframe.to_csv(f"{path}my_transcription.csv", index=False, header=False) # запись в .csv


# метод для записи данных в .txt файл:
def write_to_txt_file(our_dict: dict, path: str):
    # запись данных в .txt формат:
    with open(f"{path}my_transcription.txt", mode="w") as textFile:
        for key in our_dict:
            textFile.write(f"{key},{our_dict[key]}\n")



# main функция: обращение к браузера, получение текстовых данных, запись в файлы, поиск поиск совпадений:
def main(url: str, insert_by_user_text: str):
    driver = open_url_in_edge(url) # вызов метода для открытия драйвера по указанному url на видео в YouTube

    returned_text = get_transcript(driver) # вызов метода для получения текста из видео

    if returned_text == "":
        return "Sorry, this video does not have an apportynity to get transcription. Maybe this video is too old. Please, try again with another one..."

    driver.close() # закрытие браузера, работаюшего в фоновом режиме.

    dictionary = make_dictionary(returned_text) # вызов метода для формирование словаря: ключ - время | значение - текст

    # создание папки, если таковая отсутвует:
    if not os.path.exists("./output"):
        os.makedirs("./output")

    path_to_output_dir = "./output/" # путь до выходной папки

    print(">>> Start saving transcription <<<")
    write_to_csv_file(dictionary, path_to_output_dir)
    write_to_txt_file(dictionary, path_to_output_dir)

    return find_some_text(dictionary, insert_by_user_text)
