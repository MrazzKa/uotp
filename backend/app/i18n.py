from fastapi import Request

SUPPORTED_LANGUAGES = {"ru", "kk"}
DEFAULT_LANGUAGE = "ru"


def get_language(request: Request) -> str:
    header = request.headers.get("accept-language", DEFAULT_LANGUAGE)
    language = header.split(",")[0].split("-")[0].lower()
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
