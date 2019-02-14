import os
import sys
import time
import pytest
import traceback
import multiprocessing

from purerpc.test_utils import run_tests_in_workers, _run_context_manager_generator_in_process


def test_run_tests_in_workers_error():
    def target_fn():
        def inner_2():
            def inner_1():
                raise ValueError("42")
            inner_1()
        inner_2()

    with pytest.raises(ValueError, match="42"):
        run_tests_in_workers(target=target_fn, num_workers=1)


def test_run_tests_in_workers_error_traceback():
    def target_fn():
        def inner_2():
            def inner_1():
                raise ValueError("42")
            inner_1()
        inner_2()

    try:
        run_tests_in_workers(target=target_fn, num_workers=1)
    except ValueError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_tb(exc_traceback)
        expected_traceback = ("target_fn", "inner_2", "inner_1")
        for expected_fname, line in zip(expected_traceback[::-1], lines[::-1]):
            assert expected_fname in line


def test_run_tests_in_workers():
    num_workers = 10
    queue = multiprocessing.Queue()
    def target_fn():
        queue.put(os.getpid())


    run_tests_in_workers(target=target_fn, num_workers=num_workers)
    pids = set()
    for _ in range(num_workers):
        pid = queue.get_nowait()
        pids.add(pid)
    assert len(pids) == num_workers


def test_run_context_manager_generator_in_process():
    def gen():
        yield 42

    with _run_context_manager_generator_in_process(gen) as result:
        assert result == 42


def test_run_context_manager_generator_in_process_error_before():
    def gen():
        raise ValueError("42")

    with pytest.raises(ValueError, match="42"):
        with _run_context_manager_generator_in_process(gen) as result:
            assert result == 42


def test_run_context_manager_generator_in_process_error_after():
    def gen():
        yield 42
        raise ValueError("42")

    with pytest.raises(ValueError, match="42"):
        with _run_context_manager_generator_in_process(gen) as result:
            assert result == 42
            time.sleep(0.1)


def test_run_context_manager_generator_in_process_error_traceback():
    def gen():
        def inner_2():
            def inner_1():
                raise ValueError("42")
            inner_1()
        inner_2()

    try:
        with _run_context_manager_generator_in_process(gen):
            pass
    except ValueError:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        lines = traceback.format_tb(exc_traceback)
        expected_traceback = ("gen", "inner_2", "inner_1")
        for expected_fname, line in zip(expected_traceback[::-1], lines[::-1]):
            assert expected_fname in line
