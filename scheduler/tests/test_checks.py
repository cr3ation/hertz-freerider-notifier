"""The startup check that keeps the sample SECRET_KEY out of production."""

from django.test import override_settings

from scheduler.checks import secret_key_check


@override_settings(DEBUG=False, SECRET_KEY='changeme')
def test_refuses_the_sample_key_with_debug_off():
    assert [error.id for error in secret_key_check(None)] == ['scheduler.E001']


@override_settings(DEBUG=True, SECRET_KEY='changeme')
def test_allows_the_sample_key_while_debugging():
    assert secret_key_check(None) == []


@override_settings(DEBUG=False, SECRET_KEY='a-long-random-key-set-in-env')
def test_accepts_a_real_key():
    assert secret_key_check(None) == []
