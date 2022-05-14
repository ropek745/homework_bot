import logging
import os
from Exceptions import EndpointException
import requests
import time
from http import HTTPStatus

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
import telegram


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler('my_logger.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code != HTTPStatus.OK:
        logger.error(f'Ошибка эндпоинта при запросе к API')
        raise EndpointException('Incorrect response code')
    else:
        return homework_statuses.json()


def check_response(response):
    """Проверяет API на корректность."""
    # The situation when the API response contains an empty dictionary
    if len(response) == 0:
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise 'Dict is empty.'
    # The data in the API response does not come in the form of a list
    if not isinstance(response['homeworks'], list):
        logger.error('Данные по ДЗ не в форме списка.')
        raise 'Incorrect type. This type not list.'
    # The API response is not of the correct type
    if not isinstance(response, dict):
        logger.error('Неверный тип ответа от API. Ответ не в форме словаря.')
        raise 'Incorrect type. This type not dict.'
    # The situation when the response from the API does not contain the homeworks key
    if 'homeworks' not in response:
        logger.error('Отсутствие ключа homeworks в ответе API.')
        raise 'Key "homeworks" not found.'
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус конкретного ДЗ."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """
    Проверяет доступность переменных окружения,
    необходимых для работы программы.
    """
    if PRACTICUM_TOKEN is None:
        logger.critical('Отсутствие ключа PRACTICUM_TOKEN!!!')
        return False
    elif TELEGRAM_TOKEN is None:
        logger.critical('Отсутствие ключа TELEGRAM_TOKEN!!!')
        return False
    elif TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствие ключа TELEGRAM_CHAT_ID!!!')
        return False
    else:
        return True


def main():
    """Основная логика работы программы."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        raise ValueError('Ошибка токена. Проверьте его наличие или корректность')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework[0])
                logger.info('Сообщение успешно отправлено')
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Ошибка при запросе к основному API: {error}')
            bot.send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
