"""
Custom exceptions for the application
"""


class AppException(Exception):
    """Base exception for application errors"""

    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class IngestionError(AppException):
    """Raised when document ingestion fails"""

    def __init__(self, message: str):
        super().__init__(message, status_code=500)


class InvalidPDFError(AppException):
    """Raised when uploaded file is not a valid PDF"""

    def __init__(self, message: str = "Invalid PDF file"):
        super().__init__(message, status_code=400)


class EmbeddingError(AppException):
    """Raised when embedding generation fails"""

    def __init__(self, message: str = "Failed to generate embeddings"):
        super().__init__(message, status_code=500)


class SearchError(AppException):
    """Raised when search operation fails"""

    def __init__(self, message: str = "Search operation failed"):
        super().__init__(message, status_code=500)


class LLMError(AppException):
    """Raised when LLM API call fails"""

    def __init__(self, message: str = "LLM API call failed"):
        super().__init__(message, status_code=500)
