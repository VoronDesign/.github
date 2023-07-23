from enum import IntEnum
from typing import Dict


class ReturnStatus(IntEnum):
    SUCCESS = 0
    WARNING = 1
    FAILURE = 2
    EXCEPTION = 3

return_status_string_map: Dict[ReturnStatus, str] = {
    ReturnStatus.SUCCESS: 'success',
    ReturnStatus.WARNING: 'warning',
    ReturnStatus.FAILURE: 'failure',
    ReturnStatus.EXCEPTION: 'exception'
}

RESULT_SUCCESS = "✅ PASSED"
RESULT_WARNING = "⚠️ WARNING"
RESULT_FAILURE = "❌ FAILURE"
RESULT_EXCEPTION = "❌ EXCEPTION"