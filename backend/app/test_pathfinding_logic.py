import math
from app.pathfinding import PathfindingService

def make_service(nodes, edges):
    svc = PathfindingService.__new__(PathfindingService)
    svc.graphs = {
        "foot": {
            "nodes": nodes,
            "current_weights": edges
        }
    }
    return svc

def test_a_star_basic():
    nodes = {
        "A": {"x": 0, "y": 0, "type": "normal", "name": "A"},
        "B": {"x": 1, "y": 0, "type": "normal", "name": "B"},
        "C": {"x": 2, "y": 0, "type": "normal", "name": "C"},
    }
    edges = {
        "A": {"B": 10},
        "B": {"A": 10, "C": 10},
        "C": {"B": 10},
    }
    svc = make_service(nodes, edges)
    path, cost = svc._run_a_star("A", "C")
    assert path == ["A", "B", "C"]
    assert cost == 20

def test_a_star_avoids_blocked_edge():
    nodes = {
        "A": {"x": 0, "y": 0, "type": "normal", "name": "A"},
        "B": {"x": 1, "y": 0, "type": "normal", "name": "B"},
        "C": {"x": 0, "y": 1, "type": "normal", "name": "C"},
        "D": {"x": 1, "y": 1, "type": "normal", "name": "D"},
    }
    edges = {
        "A": {"B": 5, "C": 7},
        "B": {"A": 5, "D": 100000},
        "C": {"A": 7, "D": 7},
        "D": {"B": 100000, "C": 7},
    }
    svc = make_service(nodes, edges)
    path, cost = svc._run_a_star("A", "D")
    assert path == ["A", "C", "D"]
    assert cost == 14

def test_a_star_no_path():
    nodes = {
        "A": {"x": 0, "y": 0, "type": "normal", "name": "A"},
        "B": {"x": 1, "y": 0, "type": "normal", "name": "B"},
        "C": {"x": 10, "y": 10, "type": "normal", "name": "C"},
    }
    edges = {
        "A": {"B": 5},
        "B": {"A": 5},
    }
    svc = make_service(nodes, edges)
    path, cost = svc._run_a_star("A", "C")
    assert path is None
    assert math.isinf(cost)

def test_a_star_same_start_end():
    nodes = {
        "A": {"x": 0, "y": 0, "type": "normal", "name": "A"},
    }
    edges = {}
    svc = make_service(nodes, edges)
    path, cost = svc._run_a_star("A", "A")
    assert path == ["A"]
    assert cost == 0

def test_get_chi_tiet_fallback_station():
    nodes = {
        "S": {"x": 0, "y": 0, "type": "normal", "name": "Start"},
        "D": {"x": 100, "y": 0, "type": "normal", "name": "Dest"},
        "GA1": {"x": 1, "y": 0, "type": "station", "name": "Station 1"},
        "GA2": {"x": 10, "y": 0, "type": "station", "name": "Station 2"},
    }
    edges = {
        "S": {"GA2": 20},
        "GA2": {"S": 20, "D": 30},
        "D": {"GA2": 30},
    }
    svc = make_service(nodes, edges)
    result = svc.get_chi_tiet_phan_4(0, 0, 100, 0)

    assert result["nhiem_vu_1"]["id_ga_di"] == "GA1"

