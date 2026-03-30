"""
API Server - Nơi nhận yêu cầu từ Giao diện và gọi Thuật toán
"""

from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import logging

# Lấy thuật toán xử lý từ file pathfinding
from app.pathfinding import PathfindingService, get_pathfinding_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kuala Lumpur Transit - First/Last Mile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/walking-legs")
async def find_walking_legs(
    start_x: float = Query(..., description="Tọa độ X điểm xuất phát"),
    start_y: float = Query(..., description="Tọa độ Y điểm xuất phát"),
    end_x: float = Query(..., description="Tọa độ X điểm đến"),
    end_y: float = Query(..., description="Tọa độ Y điểm đến"),
    service: PathfindingService = Depends(get_pathfinding_service)
):
    """
    API DÀNH RIÊNG CHO PHẦN 4:
    Tìm 1 lộ trình đi bộ ngắn nhất, an toàn nhất (tránh đường chặn) cho chặng đầu và chặng cuối.
    """
    logger.info("Đang xử lý tìm đường đi bộ chặng 1 và chặng 3...")
    
    try:
        # Gọi thẳng vào hàm chốt hạ của Phần 4
        ket_qua = service.get_chi_tiet_phan_4(start_x, start_y, end_x, end_y)
        
        return {
            "trang_thai": "thanh_cong",
            "du_lieu": ket_qua
        }
    except Exception as e:
        logger.error(f"Lỗi server: {e}")
        raise HTTPException(status_code=500, detail="Lỗi khi tính toán đường đi bộ")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)