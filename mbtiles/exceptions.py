class ExtractionError(Exception):
    """ Raised when extraction of tiles from specified MBTiles has failed """
    pass

class InvalidFormatError(Exception):
    """ Raised when reading of MBTiles content has failed """
    pass

class DownloadError(Exception):
    """ Raised when download at tiles URL fails DOWNLOAD_RETRIES times """
    def __init__(self, *args, status_code=None, **kwargs):
        self.status_code = status_code

class InvalidCoverageError(Exception):
    """ Raised when coverage bounds are invalid """
    pass

class EmptyCoverageError(Exception):
    """ Raised when coverage (tiles list) is empty """
    pass

class StopException(Exception):
    """ Raised to stop map downloading process """
    pass
