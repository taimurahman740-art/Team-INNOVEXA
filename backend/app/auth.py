"""Password hashing and signed, expiring staff bearer tokens."""
import base64, hashlib, hmac, json, os, secrets, time
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .database import get_db
from .models import StaffUser

TOKEN_LIFETIME_SECONDS = 8 * 60 * 60
PASSWORD_ITERATIONS = 310_000
bearer_scheme = HTTPBearer(auto_error=False)

def _enc(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

def _dec(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def _secret() -> bytes:
    value = os.getenv("STAFF_TOKEN_SECRET", "")
    if len(value) < 32:
        raise HTTPException(status_code=503, detail="Staff login is not configured. Set STAFF_TOKEN_SECRET to a random value of at least 32 characters.")
    return value.encode()

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PASSWORD_ITERATIONS)
    return "pbkdf2_sha256$" + str(PASSWORD_ITERATIONS) + "$" + _enc(salt) + "$" + _enc(digest)

def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256": return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), _dec(salt), int(iterations))
        return hmac.compare_digest(actual, _dec(expected))
    except (ValueError, TypeError): return False

def create_access_token(user: StaffUser) -> str:
    password_fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest()
    payload = _enc(json.dumps({"sub": user.id, "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS, "pwd": password_fingerprint}, separators=(",", ":")).encode())
    signature = hmac.new(_secret(), payload.encode(), hashlib.sha256).digest()
    return payload + "." + _enc(signature)

def decode_access_token(token: str) -> tuple[int, str]:
    try:
        payload, signature = token.split(".", 1)
        expected = hmac.new(_secret(), payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _dec(signature)): raise ValueError("signature")
        data = json.loads(_dec(payload))
        if int(data["exp"]) <= int(time.time()): raise ValueError("expired")
        return int(data["sub"]), str(data["pwd"])
    except HTTPException: raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="Staff session is invalid or expired. Please sign in again.")

def get_current_staff(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), db: Session = Depends(get_db)) -> StaffUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in with your staff email and password.")
    user_id, password_fingerprint = decode_access_token(credentials.credentials)
    user = db.get(StaffUser, user_id)
    current_fingerprint = hashlib.sha256(user.password_hash.encode()).hexdigest() if user is not None else ""
    if user is None or not user.is_active or not hmac.compare_digest(password_fingerprint, current_fingerprint): raise HTTPException(status_code=401, detail="This staff account is unavailable.")
    return user

def require_admin(user: StaffUser = Depends(get_current_staff)) -> StaffUser:
    if user.role != "admin": raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user
