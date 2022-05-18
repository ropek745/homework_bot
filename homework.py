import requests
from http import HTTPStatus
import os
import time
import logging
from logging.handlers import RotatingFileHandler


from dotenv import load_dotenv
import telegram

from exceptions import EndpointException

LOG_FILENAME = __file__ + '.log'
logging.basicConfig(
    level=logging.DEBUG,
    stream=LOG_FILENAME,
    format='%(asctime)s, %(levelname)s, %(funcName)s, %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(
    LOG_FILENAME,
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s')
handler.setFormatter(formatter)


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TOKENS = ['PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID']

NO_VALUES = 'Отсутствуют вердикты.'
NO_TOKEN = 'Токен не найден.'
PARSE_RETURN = 'Изменился статус проверки работы "{name}". {verdict}'
ERROR_MESSAGE = 'Сбой в работе программы: {error}'
DICT_ERROR = '{value} не является словарём.'
LIST_ERROR = '{value} не является списком'
EMPTY_LIST = 'Список пустой'
HOMEWORKS_ERROR = 'Ключ "homeworks" отсутствует в словаре.'
JSON_ERROR = 'Произошла ошибка {error} в json запросе!'
ENDPOINT_ERROR = 'Некорректный код ответа от {code}'
CONNECTION_ERROR = 'Ошибка соединения с {url}, {headers}, {params}'
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
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    response_settings = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': current_timestamp}
    }
    # Страховка от сбоя сети
    try:
        response = requests.get(**response_settings)
    except requests.RequestException as error:
        raise ConnectionError(CONNECTION_ERROR.format(
            error=error, **response_settings)
        )
    # Страховка на cлучай отличного от 200 кода
    if response.status_code != HTTPStatus.OK:
        raise EndpointException(
            ENDPOINT_ERROR.format(code=response.status_code)
        )
    # Страховка для отказа от обслуживания
    for error in ['code', 'error']:
        if error in response.json():
            raise ValueError(JSON_ERROR.format(error=response.json()[error],))
    return response.json()


def check_response(response):
    """Проверяет API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(DICT_ERROR.format(value=type(response)))
    if 'homeworks' not in response:
        raise KeyError(HOMEWORKS_ERROR)
    if len(response) == 0:
        raise ValueError(EMPTY_LIST)
    if not isinstance(response['homeworks'], list):
        raise TypeError(LIST_ERROR.format(value=type(response['homeworks'])))
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус конкретного ДЗ."""
    name = homework['homework_name']
    status = homework['status']
    verdict = VERDICTS[status]
    if len(verdict) == 0:
        raise ValueError(NO_VALUES)
    return PARSE_RETURN.format(name=name, verdict=verdict)


def check_tokens():
    """Проверка доступности токенов."""
    for name in TOKENS:
        if globals()[name] is None:
            return False
    return True


def main():
    """Основная логика работы программы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        raise ValueError(NO_TOKEN)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                logging.info('Сообщение успешно отправлено')
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
        except Exception as error:
            message = ERROR_MESSAGE.format(error=error)
            logging.error(message, exc_info=True)
            send_message(bot, message)
        time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
