class ContentFlaggedException(Exception):
    """Raised when the content is blocked by safety filters."""
    def __init__(self, message, context="Operation"):
        super().__init__(message)
        self.context = context