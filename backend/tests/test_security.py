from app.core.security import hash_password, verify_password
from app.utils.files import safe_extension
from fastapi import HTTPException
import pytest


def test_password_hash_is_not_plaintext():
    stored = hash_password("Engineer123!")
    assert stored != "Engineer123!"
    assert verify_password("Engineer123!", stored)
    assert not verify_password("wrong-password", stored)


def test_rejects_executable_extension():
    with pytest.raises(HTTPException):
        safe_extension("payload.exe")
