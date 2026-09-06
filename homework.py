import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import vk_api
from dotenv import load_dotenv

from exceptions import APIRequestError, APIResponseError

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)


def check_tokens():
    """Проверяет доступность обязательных переменных окружения."""
    return all([PRACTICUM_TOKEN, VK_TOKEN, VK_USER_ID])


def send_message(vk, message):
    """Отправляет сообщение в VK-чат пользователя."""
    try:
        logger.debug(f'Попытка отправить сообщение: "{message}"')
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=0
        )
        logger.debug('Сообщение успешно отправлено в VK.')
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения в VK: {error}')


def get_api_answer(timestamp):
    """Делает GET-запрос к эндпоинту API-сервиса Практикум.Домашка."""
    payload = {'from_date': timestamp}
    try:
        logger.info(f'Запрос к API: {ENDPOINT} с параметрами {payload}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        raise APIRequestError(f'Сетевая ошибка при обращении к API: {error}')

    if response.status_code != HTTPStatus.OK:
        raise APIRequestError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа: {response.status_code}'
        )

    try:
        return response.json()
    except ValueError:
        raise APIResponseError('Ответ API не является валидным JSON.')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API имеет некорректный тип (ожидался словарь).')

    if 'homeworks' not in response:
        raise APIResponseError('В ответе API отсутствует ключ "homeworks".')

    if 'current_date' not in response:
        raise APIResponseError('В ответе API отсутствует ключ "current_date".')

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError('Данные под ключом "homeworks" не являются списком.')

    return homeworks


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе её статус."""
    if 'homework_name' not in homework:
        raise KeyError('В информации о домашке отсутствует "homework_name".')

    if 'status' not in homework:
        raise KeyError('В информации о домашке отсутствует "status".')

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Недокументированный статус работы: {status}')

    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(stream=sys.stdout)]
    )

    if not check_tokens():
        logger.critical(
            'Отсутствуют переменные окружения. '
            'Работа остановлена.'
        )
        sys.exit(1)

    try:
        vk_session = vk_api.VkApi(token=VK_TOKEN)
        vk = vk_session.get_api()
    except Exception as error:
        logger.critical(f'Ошибка инициализации VK API: {error}')
        sys.exit(1)

    timestamp = int(time.time())
    last_error_message = ""

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            if homeworks:
                message = parse_status(homeworks[0])
                send_message(vk, message)
            else:
                logger.debug('В ответе нет новых статусов.')

            timestamp = response.get('current_date', timestamp)
            last_error_message = ""

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)

            if message != last_error_message:
                send_message(vk, message)
                last_error_message = message

        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
