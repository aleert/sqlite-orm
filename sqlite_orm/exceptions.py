class dbIntegrityError(Exception):
    pass


class QueryError(Exception):
    pass


class NotFoundError(Exception):
    pass


class MultipleRowsReturnedError(Exception):
    pass


class DatabaseClosedError(Exception):
    pass
