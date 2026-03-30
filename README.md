# IT3160-168453-KLMap-N6

Web app for pedestrian navigation in Kuala Lumpur.

## Hướng dẫn cài đặt và chạy localhost

Chỉ cần làm theo 3 bước dưới đây để khởi động hệ thống trên máy của bạn.

---

## 1. Cài đặt thư viện

Yêu cầu:

- Python `3.8` trở lên
- Mở Terminal hoặc Command Prompt tại thư mục gốc của project

Chạy lệnh sau để cài đặt dependencies:

```bash
pip install -r requirements.txt
```

Sau đó di chuyển vào thư mục backend:

```bash
cd IT3160-168453-KLMap-N6\backend
```

> Thuật toán đã được tối ưu bằng Python thuần và các thư viện lõi, không cần cài thêm `SciPy` hay `Pandas` để tránh lỗi môi trường.

---

## 2. Khởi động server

Tại terminal đang mở, chạy lệnh sau để bật server bằng Uvicorn:

```bash
uvicorn app.main:app --reload
```

Nếu xuất hiện dòng:

```text
Application startup complete
```

thì server đã chạy thành công tại:

```text
http://localhost:8000
```

---

## 3. Test API trực quan

Mở trình duyệt và truy cập:

```text
http://localhost:8000/docs
```

Đây là giao diện Swagger UI được tự động tạo.

### Các bước test

1. Chọn endpoint `GET /api/walking-legs`
2. Nhấn **Try it out**
3. Nhập các tham số:
   - `start_x`
   - `start_y`
   - `end_x`
   - `end_y`
4. Nhấn **Execute**
5. Xem kết quả JSON trả về

Thuật toán có thể phản hồi rất nhanh, thường trong thời gian dưới `0.1 giây`.

---

## Cấu trúc thư mục chính

```text
IT3160-168453-KLMap-N6/
├── backend/
│   ├── app/
│   ├── data/
│   └── scripts/
├── frontend/
├── requirements.txt
└── README.md
```

---

## Ghi chú

- API chạy mặc định ở cổng `8000`
- Swagger UI hỗ trợ test trực tiếp mà không cần dùng Postman
- Nên chạy lệnh trong đúng thư mục để tránh lỗi import module
