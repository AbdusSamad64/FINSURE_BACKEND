from pydantic import BaseModel
from datetime import date

class ReportRequest(BaseModel):
    reportType: str
    startDate: date
    endDate: date
