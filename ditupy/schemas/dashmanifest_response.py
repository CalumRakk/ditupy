from pydantic import BaseModel


class ApiResponse(BaseModel):
    resultCode: str
    message: str
    errorDescription: str
    resultObj: dict
    systemTime: int
