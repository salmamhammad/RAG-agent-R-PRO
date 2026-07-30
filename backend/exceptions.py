
class RateLimitExceeded(Exception):
    """Исключение, выбрасываемое при превышении лимита запросов к внешнему API."""
    pass