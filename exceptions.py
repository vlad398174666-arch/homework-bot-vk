class APIRequestError(Exception):
    """Сбой при отправке запроса к API Практикума."""
    pass

class APIResponseError(Exception):
    """Неожиданная структура или содержимое ответа от API."""
    pass
