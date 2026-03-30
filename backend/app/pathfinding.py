"""
File: pathfinding.py
Mô tả: Thuật toán tìm đường đi bộ ngắn nhất, an toàn nhất
"""
 
import math
import heapq
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)
# Define hằng số phạt cho route bị chặn, cản
BLOCKED_EDGE_THRESHOLD = 100000

class PathfindingService:
    def __init__(self):
        # Khởi tạo bản đồ rỗng trong RAM
        self.graphs = {
            'foot': {'nodes': {}, 'current_weights': {}}
        }
        # Tự động nạp dữ liệu ngay khi khởi động server
        self.load_graph_from_db()

    def load_graph_from_db(self):
        # Tìm file pathfinding.db (Thử ở thư mục data trước, nếu không có thì tìm ở thư mục hiện tại)
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'pathfinding.db')
        if not os.path.exists(db_path):
            db_path = 'pathfinding.db' 
            
        if not os.path.exists(db_path):
            logger.error(f"❌ KHÔNG TÌM THẤY FILE DATABASE TẠI: {db_path}")
            return

        logger.info("Đang nạp dữ liệu bản đồ đi bộ vào RAM...")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 1. Đọc danh sách các điểm (Nodes)
            cursor.execute("SELECT id, x, y, type, name FROM nodes")
            for row in cursor.fetchall():
                node_id, x, y, n_type, name = str(row[0]), float(row[1]), float(row[2]), str(row[3]), str(row[4])
                self.graphs['foot']['nodes'][node_id] = {
                    'x': x, 'y': y, 'type': n_type, 'name': name
                }

            # 2. Đọc danh sách các đoạn đường (Edges)
            cursor.execute("SELECT node_from, node_to, weight FROM edges")
            for row in cursor.fetchall():
                u, v, weight = str(row[0]), str(row[1]), float(row[2])
                
                if u not in self.graphs['foot']['current_weights']:
                    self.graphs['foot']['current_weights'][u] = {}
                if v not in self.graphs['foot']['current_weights']:
                    self.graphs['foot']['current_weights'][v] = {}
                    
                # Đi bộ được đi 2 chiều nên lưu cả u->v và v->u
                self.graphs['foot']['current_weights'][u][v] = weight
                self.graphs['foot']['current_weights'][v][u] = weight

            conn.close()
            logger.info(f"✅ Đã nạp xong {len(self.graphs['foot']['nodes'])} điểm giao cắt!")
        except Exception as e:
            logger.error(f"❌ Lỗi đọc DB: {e}")

    def _run_a_star(self, start_node, end_node, vehicle='foot'):
        nodes = self.graphs[vehicle]['nodes']
        edges = self.graphs[vehicle]['current_weights']
        
        if start_node not in nodes or end_node not in nodes:
            return None, float('inf')

        end_x, end_y = nodes[end_node]['x'], nodes[end_node]['y']

        # Hàm Heuristic: Khoảng cách đường chim bay chia cho tốc độ đi bộ (1.4 m/s)
        def heuristic(node_id):
            nx, ny = nodes[node_id]['x'], nodes[node_id]['y']
            return math.hypot(nx - end_x, ny - end_y) 

        open_set = []
        heapq.heappush(open_set, (heuristic(start_node), 0, start_node))
        came_from = {}
        g_score = {start_node: 0}

        while open_set:
            _, current_g, current = heapq.heappop(open_set)

            if current == end_node:
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path, current_g

            if current_g > g_score.get(current, float('inf')):
                continue

            if current in edges:
                for neighbor, weight in edges[current].items():
                    # NẾU ADMIN CHẶN ĐƯỜNG: Bỏ qua ngã rẽ này
                    if weight >= BLOCKED_EDGE_THRESHOLD: 
                        continue
                        
                    tentative_g = current_g + weight
                    if tentative_g < g_score.get(neighbor, float('inf')):
                        came_from[neighbor] = current
                        g_score[neighbor] = tentative_g
                        f_score = tentative_g + heuristic(neighbor)
                        heapq.heappush(open_set, (f_score, tentative_g, neighbor))
                        
        return None, float('inf')

    # =========================================================================
    # HÀM CHÍNH CỦA PHẦN 4: GIAO TIẾP VỚI FRONTEND VÀ PHẦN 3
    # =========================================================================
    def get_chi_tiet_phan_4(self, start_x: float, start_y: float, end_x: float, end_y: float):
        """
        NHIỆM VỤ PHẦN 4: 
        Tìm đường đi bộ hợp lệ ngắn nhất, có cơ chế Fallback chống kẹt đường 
        và chống lỗi "Node cô lập" (Disconnected Subgraph).
        """
        try:
            nodes = self.graphs['foot']['nodes']
            if not nodes:
                raise ValueError("Bản đồ rỗng! Kiểm tra lại file pathfinding.db")

            station_nodes = [n_id for n_id, data in nodes.items() if data.get('type') == 'station']

            # ==========================================================
            # 1. TÌM K ĐIỂM XUẤT PHÁT/ĐÍCH GẦN NHẤT (Chống lỗi Node cô lập)
            # ==========================================================
            def find_k_nearest_nodes(tx, ty, k=3):
                distances = []
                for n_id, data in nodes.items():
                    dist = math.hypot(data['x'] - tx, data['y'] - ty)
                    distances.append((dist, n_id))
                
                # Sắp xếp từ gần đến xa và lấy K điểm đầu tiên
                distances.sort(key=lambda x: x[0])
                return [n_id for _, n_id in distances[:k]]

            # Lấy 3 ứng cử viên cho điểm xuất phát và 3 ứng cử viên cho điểm đích
            start_candidates = find_k_nearest_nodes(start_x, start_y, k=3)
            end_candidates = find_k_nearest_nodes(end_x, end_y, k=3)
            # ==========================================================
            # 2. TÌM LỘ TRÌNH TỐT NHẤT THỰC TẾ TỪ CÁC ỨNG CỬ VIÊN
            # ==========================================================
            def find_best_path(candidates, is_start_leg=True):
                best_cost_m = float('inf')
                best_result = (None, None, float('inf')) # (ga_id, path, cost_giay)

                for origin_node in candidates:
                    orig_data = nodes[origin_node]
                    
                    # Bước A: Tính khoảng cách chim bay đến TẤT CẢ các ga
                    station_distances = []
                    for st_id in station_nodes:
                        st_data = nodes[st_id]
                        dist = math.hypot(orig_data['x'] - st_data['x'], orig_data['y'] - st_data['y'])
                        station_distances.append((dist, st_id))
                    
                    # Bước B: CHỈ LẤY TOP 5 GA GẦN NHẤT (Đường chim bay)
                    # Giúp server không bị treo vì phải chạy A* hàng trăm lần
                    station_distances.sort(key=lambda x: x[0])
                    top_5_stations = [st_id for _, st_id in station_distances[:5]]

                    # Bước C: Chạy A* cho cả 5 ga này để tìm ra LỘ TRÌNH THỰC TẾ NGẮN NHẤT
                    for st_id in top_5_stations:
                        source = origin_node if is_start_leg else st_id
                        target = st_id if is_start_leg else origin_node
                        
                        path, cost_m = self._run_a_star(source, target, vehicle='foot')
                        
                        # So sánh để tìm kỷ lục quãng đường ngắn nhất
                        if path and cost_m < BLOCKED_EDGE_THRESHOLD:
                            if cost_m < best_cost_m:
                                best_cost_m = cost_m
                                thoi_gian_giay = cost_m / 1.4
                                best_result = (st_id, path, thoi_gian_giay)
                            
                    # Chú ý: Đã XÓA lệnh `break` ở đây. 
                    # Thuật toán giờ đây sẽ kiên nhẫn quét hết các lựa chọn để tìm ra "chân ái" rẻ nhất!
                                  
                return best_result

            # 3. Thực thi tìm 2 chặng
            ga_di, duong_ra_ga_di, thoi_gian_ra_ga = find_best_path(start_candidates, is_start_leg=True)
            ga_den, duong_ve_dich, thoi_gian_ve_dich = find_best_path(end_candidates, is_start_leg=False)

            # 4. Trả về kết quả
            def format_thoi_gian(thoi_gian):
                # Nếu là vô cực (inf), trả về None để Frontend nhận được giá trị 'null'
                return round(thoi_gian, 2) if thoi_gian != float('inf') else None

            return {
                "nhiem_vu_1": {
                    "mo_ta": "Đường đi bộ ngắn nhất từ Vị trí xuất phát đến Ga đi",
                    "id_ga_di": ga_di,
                    "ten_ga_di": nodes[ga_di].get('name') if ga_di else "Lỗi: Xung quanh bị chặn kín",
                    "thoi_gian_di_bo_giay": format_thoi_gian(thoi_gian_ra_ga),
                    "lo_trinh_nguyen_ban": duong_ra_ga_di or []
                },
                "nhiem_vu_2": {
                    "mo_ta": "Đường đi bộ ngắn nhất từ Ga đến về Vị trí đích",
                    "id_ga_den": ga_den,
                    "ten_ga_den": nodes[ga_den].get('name') if ga_den else "Lỗi: Xung quanh bị chặn kín",
                    "thoi_gian_di_bo_giay": format_thoi_gian(thoi_gian_ve_dich),
                    "lo_trinh_nguyen_ban": duong_ve_dich or []
                }
            }
        except Exception as e:
            logger.error(f"Lỗi ở logic Phần 4: {str(e)}")
            raise e
        
# Tạo instance duy nhất (Singleton) để dùng chung
pathfinding_service_instance = PathfindingService()
def get_pathfinding_service():
    return pathfinding_service_instance