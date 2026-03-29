import json
import math
import csv
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

# Giới hạn map
lonLeft = 101.50
lonRight = 101.80
latTop = 3.30
latBottom = 3.00

# Kích thước ảnh
WIDTH = 8000
HEIGHT = 8000

# Tùy chỉnh bộ lọc mạng lưới đường đi bộ
EXTRACT_FOOTWAY = True       # Ưu tiên lấy đường đi bộ chuyên dụng
EXTRACT_RESIDENTIAL = True   # Lấy đường trong khu dân cư
EXTRACT_PRIMARY = False      # Bỏ qua các đường quốc lộ, cao tốc lớn do đi bộ không được phép

@dataclass
class Node:
    id: int
    lat: float
    lon: float
    tags: Dict[str, Any]
    type: str = "intersection" # Mặc định là điểm giao cắt
    name: str = ""
    x: Optional[float] = None  # Tọa độ X khi vẽ lên mặt phẳng 2D
    y: Optional[float] = None  # Tọa độ Y khi vẽ lên mặt phẳng 2D

@dataclass
class Edge:
    start: int                 # Node ID xuất phát
    end: int                   # Node ID kết thúc
    tags: Dict[str, Any]
    weight: Optional[float] = None


def load_osm_json(path: str):
    # Tải dữ liệu bản đồ thô JSON được trích xuất từ OpenStreetMap 
    print(f"Bắt đầu đọc file dữ liệu bản đồ: {path}...")
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def extract_nodes_and_stations(data: List[Dict[str, Any]]) -> Dict[int, Node]:
    # Quét file JSON để tìm ra toàn bộ các điểm Node và Nhà ga tàu.
    nodes = {}
    for obj in data:
        if obj.get("type") == "node":
            nid = obj["id"]
            tags = obj.get("tags", {})
            node_type = "intersection"
            name = tags.get("name", "")
            
            # Phân tích toàn bộ hệ thống Ga tàu (MRT, LRT, Monorail)
            rail_tag = tags.get("railway", "")
            stat_tag = tags.get("station", "")
            pub_tag = tags.get("public_transport", "")
            
            if (rail_tag in ["station", "stop"] or 
                stat_tag in ["subway", "light_rail", "monorail"] or 
                pub_tag == "stop_position"):
                node_type = "station"
            
            nodes[nid] = Node(id=nid, lat=obj["lat"], lon=obj["lon"], tags=tags, type=node_type, name=name)
    return nodes

def should_extract_highway(tags: Dict[str, Any]) -> bool:
    # Bộ lọc kiểm tra xem một cung đường có phù hợp cho người đi bộ hay không. 
    highway_tag = tags.get("highway")
    if not highway_tag:
        return False
    
    # Giữ lại các con đường nhỏ, vỉa hè, hẻm và đường nội khu
    if EXTRACT_FOOTWAY and highway_tag in {"footway", "pedestrian", "path", "steps", "cycleway", "corridor"}:
        return True
    if EXTRACT_RESIDENTIAL and highway_tag in {"residential", "living_street", "unclassified", "service"}:
        return True
    return False

def extract_edges(data: List[Dict[str, Any]]) -> List[Edge]:
    # Trích xuất các dải đường đi bộ và chuyển hóa thành các Cạnh (Edges) nối liền các Node.
    edges = []
    for obj in data:
        if obj.get("type") == "way":
            tags = obj.get("tags", {})
            if not should_extract_highway(tags):
                continue
            
            node_list = obj.get("nodes", [])
            for i in range(len(node_list) - 1):
                edges.append(Edge(start=node_list[i], end=node_list[i + 1], tags=tags))
    return edges

def convert_coords(nodes: Dict[int, Node]):
    # Quy đổi từ hệ Kinh/Vĩ độ thực (Lat/Lon) sang hệ trục tọa độ Pixel Descartes (X, Y).
    for node in nodes.values():
        node.x = (node.lon - lonLeft) / (lonRight - lonLeft) * WIDTH
        # Trục Y của bản đồ đi từ Bắc xuống Nam (vĩ độ giảm dần) nên cần đảo ngược
        node.y = (latTop - node.lat) / (latTop - latBottom) * HEIGHT

def add_bidirectional_edges(edges: List[Edge]) -> List[Edge]:
    # Với mạng lưới đi bộ, người dùng có thể đi lại 2 chiều tự do.
    new_edges = []
    for edge in edges:
        is_oneway = edge.tags.get("oneway") == "yes"
        if not is_oneway:
            new_edges.append(Edge(start=edge.end, end=edge.start, tags=edge.tags))
    return new_edges

def remove_duplicates(edges: List[Edge]) -> List[Edge]:
    # Dọn dẹp đồ thị bằng cách xoá bỏ các cạnh bị khai báo trùng lặp.
    seen = set()
    unique = []
    for e in edges:
        tup = (e.start, e.end)
        if tup not in seen:
            unique.append(e)
            seen.add(tup)
    return unique

def calculate_weights(nodes: Dict[int, Node], edges: List[Edge]):
    # Áp dụng công thức tính khoảng cách thực tế (theo Hệ mét) làm trọng số Cost cho mỗi cung đường.
    for edge in edges:
        start_node = nodes.get(edge.start)
        end_node = nodes.get(edge.end)
        if start_node and end_node:
            # Sử dụng công thức Euclidean xấp xỉ tỉ lệ Lat/Lon ra mm (1 vĩ độ ~ 111km)
            dist = math.sqrt((start_node.lon - end_node.lon)**2 + (start_node.lat - end_node.lat)**2) * 111000 
            edge.weight = dist

def subdivide_edges(nodes: Dict[int, Node], edges: List[Edge], limit_meters=50.0) -> List[Edge]:
    # Hàm chia nhỏ các cung đường thẳng bị dài quá ngưỡng cho phép.
    new_edges = []
    subdivided_count = 0
    
    # Khởi tạo ID an toàn cho các Node nội suy (được tạo mới)
    new_node_id = max(nodes.keys()) + 1 if nodes else 1
    cache = {}
    
    for edge in edges:
        start_node = nodes.get(edge.start)
        end_node = nodes.get(edge.end)
        if not start_node or not end_node:
            continue
            
        dist = math.sqrt((start_node.lon - end_node.lon)**2 + (start_node.lat - end_node.lat)**2) * 111000
        
        # Giữ nguyên nếu khoảng cách đã đạt chuẩn ngắn
        if dist <= limit_meters:
            new_edges.append(edge)
            continue
            
        subdivided_count += 1
        
        # Canonical đảm bảo cạnh AB và BA sẽ dùng chung một bộ Node nội suy đã băm
        canonical = tuple(sorted((edge.start, edge.end)))
        
        if canonical in cache:
            intermediate_nodes = cache[canonical]
            if edge.start > edge.end:
                path = [edge.start] + intermediate_nodes[::-1] + [edge.end]
            else:
                path = [edge.start] + intermediate_nodes + [edge.end]
                
            for i in range(len(path) - 1):
                new_edges.append(Edge(start=path[i], end=path[i+1], tags=edge.tags))
        else:
            num_segments = math.ceil(dist / limit_meters)
            intermediate_nodes = []
            last_id = edge.start
            
            # Nội suy và cắm cọc nối vào Graph
            for i in range(1, int(num_segments)):
                ratio = i / num_segments
                n_lon = start_node.lon + ratio * (end_node.lon - start_node.lon)
                n_lat = start_node.lat + ratio * (end_node.lat - start_node.lat)
                n_x = start_node.x + ratio * (end_node.x - start_node.x) if start_node.x is not None else None
                n_y = start_node.y + ratio * (end_node.y - start_node.y) if start_node.y is not None else None
                
                new_node = Node(id=new_node_id, lat=n_lat, lon=n_lon, tags={}, type="intersection", x=n_x, y=n_y)
                nodes[new_node_id] = new_node
                intermediate_nodes.append(new_node_id)
                
                new_edges.append(Edge(start=last_id, end=new_node_id, tags=edge.tags))
                last_id = new_node_id
                new_node_id += 1
                
            new_edges.append(Edge(start=last_id, end=edge.end, tags=edge.tags))
            
            # Lưu lại vào Cache
            if edge.start < edge.end:
                cache[canonical] = intermediate_nodes
            else:
                cache[canonical] = intermediate_nodes[::-1]
                
    print(f"-> Đã chia nhỏ {subdivided_count} phân đoạn đường quá dài thành các đốt < {limit_meters}m.")
    return new_edges


def main(input_file: str):
    json_data = load_osm_json(input_file)
    elements = json_data.get("elements", [])

    print("\n1. Đang trích xuất dữ liệu gốc...")
    nodes = extract_nodes_and_stations(elements)
    edges = extract_edges(elements)
    print(f"Tổng số điểm ban đầu: {len(nodes)} điểm, {len(edges)} đoạn đường.")

    print("\n2. Quy đổi tọa độ Hệ mặt phẳng (X, Y)...")
    convert_coords(nodes)

    print("3. Cấu hình mô hình đường hai chiều cho giao thông bộ...")
    edges.extend(add_bidirectional_edges(edges))
    
    # Loại bỏ toàn bộ Node nằm văng ra khỏi khu vực bản đồ đã khai báo ban đầu.
    nodes = {nid: node for nid, node in nodes.items() if lonLeft <= node.lon <= lonRight and latBottom <= node.lat <= latTop}
    edges = [edge for edge in edges if edge.start in nodes and edge.end in nodes]

    print("\n4. Chia nhỏ các đường đi bộ bị dài quá ngưỡng...")
    edges = subdivide_edges(nodes, edges, limit_meters=50.0)

    print("5. Tính toán trọng số khoảng cách...")
    calculate_weights(nodes, edges)

    print("6. Làm sạch biểu đồ")
    edges = remove_duplicates(edges)
    
    # Chỉ giữ lại những Node nào đã nối thành công với mạng lưới để không bị đứt đoạn 
    nodes_in_use = {edge.start for edge in edges} | {edge.end for edge in edges}
    for nid, node in nodes.items():
        if node.type == "station":
            nodes_in_use.add(nid) # Vẫn bảo tồn riêng thông tin Nhà Ga tàu
            
    nodes = {nid: node for nid, node in nodes.items() if nid in nodes_in_use}
    print(f"-> Chốt hạ lại lưới: {len(nodes)} Nút (Điểm giao cắt) và {len(edges)} Cung đường liên kết.")

    print("\n7. Đóng gói ra định dạng thô CSV...")
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    nodes_out = os.path.join(BASE_DIR, "nodes.csv")
    edges_out = os.path.join(BASE_DIR, "edges.csv")

    with open(nodes_out, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["id", "lat", "lon", "x", "y", "type", "name"])
        writer.writerows([[n.id, n.lat, n.lon, n.x, n.y, n.type, n.name] for n in nodes.values()])

    with open(edges_out, "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["source", "target", "distance"])
        writer.writerows([[e.start, e.end, e.weight] for e in edges])
        
    print("\nFile `nodes.csv` và `edges.csv` sinh thành công!")

if __name__ == "__main__":
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(BASE_DIR, "kl_map.json")
    main(file_path)
