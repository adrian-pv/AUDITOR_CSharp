"""
Hash de contraseñas con scrypt (biblioteca estándar de Python, sin
dependencias externas). Nunca se guarda la contraseña en texto plano:
solo `scrypt$<sal>$<hash>`.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

_N, _R, _P = 2**14, 8, 1


def hashear(contrasena: str) -> str:
    sal = secrets.token_bytes(16)
    h = hashlib.scrypt(contrasena.encode(), salt=sal, n=_N, r=_R, p=_P)
    return f"scrypt${sal.hex()}${h.hex()}"


def verificar(contrasena: str, almacenado: str) -> bool:
    try:
        algoritmo, sal_hex, hash_hex = almacenado.split("$")
    except ValueError:
        return False
    if algoritmo != "scrypt":
        return False
    h = hashlib.scrypt(contrasena.encode(), salt=bytes.fromhex(sal_hex), n=_N, r=_R, p=_P)
    return hmac.compare_digest(h.hex(), hash_hex)
