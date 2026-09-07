class APIRequestError(Exception):
    """Кастомное исключение при сбое запроса к API."""


class APIResponseError(Exception):
    """Кастомное исключение при некорректном ответе API."""


class SendMessageError(Exception):
    """Кастомное исключение при сбое отправки сообщения в VK."""