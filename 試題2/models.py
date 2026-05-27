"""
試題 2 - Pydantic 資料模型

定義 API 的 Request / Response 格式。
FastAPI 會自動根據這些模型：
  - 驗證傳入的 JSON（欄位缺失 → 自動回 422）
  - 產生 Swagger UI 的文件與範例
"""
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """POST /query 的 Request Body。"""
    city:     str = Field(..., example="台北市", description="縣市名稱")
    township: str = Field(..., example="大安區", description="鄉鎮市區名稱")


class DoorPlateRecord(BaseModel):
    """單筆門牌編訂記錄。"""
    city:              str
    township:          str
    village:           str | None
    address:           str | None
    registration_date: str | None
    registration_type: str | None


class QueryResponse(BaseModel):
    """POST /query 的 Response Body。"""
    city:     str
    township: str
    total:    int = Field(..., description="符合條件的總筆數（不受分頁影響）")
    count:    int = Field(..., description="本頁實際回傳筆數")
    limit:    int = Field(..., description="每頁筆數")
    offset:   int = Field(..., description="跳過筆數")
    data:     list[DoorPlateRecord]


class HealthResponse(BaseModel):
    """GET /health 的 Response Body。"""
    status:    str
    db:        str
    timestamp: str
