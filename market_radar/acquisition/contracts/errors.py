from __future__ import annotations
from enum import Enum
from typing import Any


class AcquisitionErrorCode(str, Enum):
    SOURCE_NOT_REGISTERED = "SOURCE_NOT_REGISTERED"
    SOURCE_DISABLED = "SOURCE_DISABLED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    RATE_LIMITED = "RATE_LIMITED"
    HTTP_TIMEOUT = "HTTP_TIMEOUT"
    HTTP_CLIENT_ERROR = "HTTP_CLIENT_ERROR"
    HTTP_SERVER_ERROR = "HTTP_SERVER_ERROR"
    UNSUPPORTED_CONTENT_TYPE = "UNSUPPORTED_CONTENT_TYPE"
    PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"
    INVALID_ENCODING = "INVALID_ENCODING"
    RAW_PAYLOAD_MISSING = "RAW_PAYLOAD_MISSING"
    EXTRACTION_EMPTY = "EXTRACTION_EMPTY"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"
    TIMESTAMP_MISSING = "TIMESTAMP_MISSING"
    TIMESTAMP_CONFLICT = "TIMESTAMP_CONFLICT"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    REVISION_CONFLICT = "REVISION_CONFLICT"
    ARCHIVE_UNAVAILABLE = "ARCHIVE_UNAVAILABLE"
    REPLAY_TIME_INVALID = "REPLAY_TIME_INVALID"
    SECRET_REDACTED = "SECRET_REDACTED"
    DNS_ERROR = "DNS_ERROR"
    CONNECT_TIMEOUT = "CONNECT_TIMEOUT"
    READ_TIMEOUT = "READ_TIMEOUT"
    REDIRECT_LOOP = "REDIRECT_LOOP"
    TLS_ERROR = "TLS_ERROR"
    PARSE_ERROR = "PARSE_ERROR"


class AcquisitionError(Exception):
    """Serialisable, safe error that does not contain secrets."""
    def __init__(
        self,
        code: AcquisitionErrorCode | str,
        message: str = "",
        source_id: str = "",
        url: str = "",
        http_status: int | None = None,
        retry_after: float | None = None,
        diagnostics_ref: str = "",
        details: dict | None = None,
    ):
        self.code = code if isinstance(code, AcquisitionErrorCode) else AcquisitionErrorCode(code) if isinstance(code, str) and code in AcquisitionErrorCode._value2member_map_ else code
        self.message = message
        self.source_id = source_id
        self.url = url
        self.http_status = http_status
        self.retry_after = retry_after
        self.diagnostics_ref = diagnostics_ref
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {
            "code": str(self.code.value) if isinstance(self.code, AcquisitionErrorCode) else str(self.code),
            "message": self.message, "source_id": self.source_id,
            "url": self.url, "http_status": self.http_status,
            "retry_after": self.retry_after, "diagnostics_ref": self.diagnostics_ref,
            "details": self.details or {},
        }
