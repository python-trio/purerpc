from typing import Iterable
from contextlib import contextmanager
import sys

if sys.version_info < (3, 11):
    from exceptiongroup import ExceptionGroup


def _unroll_exceptions(
    exceptions: Iterable[Exception]
) -> Iterable[Exception]:
    res: list[Exception] = []
    for exc in exceptions:
        if isinstance(exc, ExceptionGroup):
            res.extend(_unroll_exceptions(exc.exceptions))

        else:
            res.append(exc)
    return res


@contextmanager
def unwrap_exceptiongroups_single():
    try:
        yield
    except ExceptionGroup as e:
        exceptions = _unroll_exceptions(e.exceptions)

        assert len(exceptions) == 1, "Exception group contains multiple exceptions"

        raise exceptions[0]
