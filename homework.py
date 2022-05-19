import requests
import os
import time
import logging

from dotenv import load_dotenv
import telegram


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID')

SEND_MESSAGE_ERROR = 'Ошибка {error} при отправке сообщения!'
SEND_MESSAGE_SUCCSES = 'Сообщение {message} успешно отправлено!'
UNKNOWN_STATUS = 'Неизвестный статуc {status}'
NO_VALUES = 'Отсутствуют вердикты.'
TOKENS_ERROR = 'Отсутствует токен {token}'
NO_TOKEN = 'Токен {token} не найден.'
PARSE_RETURN = 'Изменился статус проверки работы "{name}". {verdict}'
ERROR_MESSAGE = 'Сбой в работе программы: {error}'
TYPE_ERROR_1 = ('Ответ запроса вернул некорректный тип данных "{type}".'
                'Ожидался словарь.')
TYPE_ERROR_2 = ('Ответ запроса вернул некорректный тип данных "{type}".'
                'Ожидался "list".')
EMPTY_LIST = 'Список пустой'
HOMEWORKS_ERROR = 'Ключ "homeworks" отсутствует в словаре.'
RESPONSE_JSON_ERROR = ('Произошла ошибка {error_key}. Параметры: {error}'
                       '{url}, {headers}, {params}')
HTTPSTATUS_ERROR = ('Некорректный код ответа от {code}.'
                    'Параметры запроса: {url}, {headers}, {params}')
CONNECTION_ERROR = 'Ошибка соединения {error} с {url}, {headers}, {params}'
RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(SEND_MESSAGE_SUCCSES.format(message=message))
        return True
    except telegram.error.TelegramError as error:
        logging.info(SEND_MESSAGE_ERROR.format(error=error, message=message))
        return False


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    request_settings = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp}
    }
    # Страховка от сбоя сети
    try:
        response = requests.get(**request_settings)
    except requests.RequestException as error:
        raise ConnectionError(CONNECTION_ERROR.format(
            error=error, **request_settings)
        )
    # Страховка на cлучай отличного от 200 кода
    if response.status_code != 200:
        raise ValueError(
            HTTPSTATUS_ERROR.format(
                code=response.status_code, **request_settings)
        )
    # Страховка для отказа от обслуживания
    response_json = response.json()
    for error in ['code', 'error']:
        if error in response_json:
            raise ValueError(RESPONSE_JSON_ERROR.format(
                error_key=response_json[error],
                error=error,
                **request_settings)
            )
    return response_json


def check_response(response):
    """Проверяет API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(TYPE_ERROR_1.format(type=type(response)))
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_ERROR)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(TYPE_ERROR_2.format(type=type(homeworks)))
    return homeworks


def parse_status(homework):
    """Извлекает статус конкретного ДЗ."""
    name = homework['homework_name']
    status = homework['status']
    if status not in VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status=status))
    return PARSE_RETURN.format(
        name=name,
        verdict=VERDICTS[status]
    )


def check_tokens():
    """Проверка доступности токенов."""
    errors = []
    for name in TOKENS:
        if globals()[name] is None:
            errors.append(name)
    if errors:
        logging.critical(TOKENS_ERROR.format(token=errors))
        return False
    return True


def main():
    """Основная логика работы программы."""
    if not check_tokens():
        raise ValueError(NO_TOKEN)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                print(check_response)
                send_message(bot, message)
                current_timestamp = response.get(
                    'current_date', current_timestamp)
        except Exception as error:
            message = ERROR_MESSAGE.format(error=error)
            logging.error(message, exc_info=True)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    LOG_FILENAME = __file__ + '.log'
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.FileHandler(LOG_FILENAME, 'w', 'utf-8'),
            logging.StreamHandler()
        ],
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    print(__file__)
    main()
