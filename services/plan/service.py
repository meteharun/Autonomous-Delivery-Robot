"""
Plan Service - Creates adaptation plans with A* pathfinding.
Listens to: ANALYZE_RESULT
Publishes to: PLAN_RESULT
"""
import sys
import heapq
from itertools import permutations

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics

OBSTACLE = 1


# ==================== A* PATHFINDING ====================

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(grid, pos):
    row, col = pos
    height = len(grid['grid'])
    width = len(grid['grid'][0])
    
    candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
    valid = []
    
    for r, c in candidates:
        if not (0 <= r < height and 0 <= c < width):
            continue
        if grid['grid'][r][c] == OBSTACLE:
            continue
        if [r, c] in grid['dynamic_obstacles']:
            continue
        valid.append((r, c))
    
    return valid


def find_path(grid, start, goal):
    start = tuple(start)
    goal = tuple(goal)
    
    if start == goal:
        return [list(start)]
    
    if grid['grid'][goal[0]][goal[1]] == OBSTACLE:
        return None
    if list(goal) in grid['dynamic_obstacles']:
        return None
    
    counter = 0
    frontier = [(0, counter, start, [start])]
    visited = set()
    
    while frontier:
        _, _, current, path = heapq.heappop(frontier)
        
        if current in visited:
            continue
        visited.add(current)
        
        if current == goal:
            return [list(p) for p in path]
        
        for neighbor in get_neighbors(grid, current):
            if neighbor not in visited:
                new_path = path + [neighbor]
                g_score = len(new_path) - 1
                h_score = heuristic(neighbor, goal)
                counter += 1
                heapq.heappush(frontier, (g_score + h_score, counter, neighbor, new_path))
    
    return None


def calculate_distance(grid, pos1, pos2):
    path = find_path(grid, pos1, pos2)
    return len(path) - 1 if path else float('inf')


# ==================== DELIVERY PLANNING ====================

def plan_delivery_sequence(grid, start_pos, delivery_locations, return_to_base):
    if not delivery_locations:
        return []
    if len(delivery_locations) == 1:
        return [delivery_locations[0]]
    if len(delivery_locations) <= 5:
        return find_optimal_sequence(grid, start_pos, delivery_locations, return_to_base)
    return nearest_neighbor_sequence(grid, start_pos, delivery_locations)


def find_optimal_sequence(grid, start_pos, delivery_locations, return_to_base):
    start_pos = tuple(start_pos)
    return_to_base = tuple(return_to_base)
    delivery_tuples = [tuple(loc) for loc in delivery_locations]
    
    all_points = [start_pos] + delivery_tuples + [return_to_base]
    distance_cache = {}
    
    for p1 in all_points:
        for p2 in all_points:
            if p1 != p2 and (p1, p2) not in distance_cache:
                dist = calculate_distance(grid, p1, p2)
                distance_cache[(p1, p2)] = dist
                distance_cache[(p2, p1)] = dist
    
    best_sequence = None
    best_total = float('inf')
    best_sum = float('inf')
    
    for perm in permutations(delivery_tuples):
        total = 0
        sum_times = 0
        cumulative = 0
        current = start_pos
        valid = True
        
        for delivery in perm:
            dist = distance_cache.get((current, delivery), float('inf'))
            if dist == float('inf'):
                valid = False
                break
            cumulative += dist
            sum_times += cumulative
            total += dist
            current = delivery
        
        if valid:
            return_dist = distance_cache.get((current, return_to_base), float('inf'))
            if return_dist != float('inf'):
                total += return_dist
            else:
                valid = False
        
        if valid and (total < best_total or (total == best_total and sum_times < best_sum)):
            best_total = total
            best_sum = sum_times
            best_sequence = list(perm)
    
    if best_sequence:
        return [list(p) for p in best_sequence]
    return nearest_neighbor_sequence(grid, start_pos, delivery_locations)


def nearest_neighbor_sequence(grid, start_pos, delivery_locations):
    sequence = []
    remaining = [list(loc) for loc in delivery_locations]
    current = list(start_pos)
    
    while remaining:
        nearest = None
        min_dist = float('inf')
        
        for loc in remaining:
            dist = calculate_distance(grid, current, loc)
            if dist < min_dist:
                min_dist = dist
                nearest = loc
        
        if nearest is None:
            break
        
        sequence.append(nearest)
        remaining.remove(nearest)
        current = nearest
    
    return sequence


def create_full_path(grid, start_pos, delivery_sequence, return_to_base):
    full_path = []
    current = start_pos
    
    for delivery in delivery_sequence:
        segment = find_path(grid, current, delivery)
        if segment is None:
            return None
        if full_path:
            full_path.extend(segment[1:])
        else:
            full_path.extend(segment)
        current = delivery
    
    return_segment = find_path(grid, current, return_to_base)
    if return_segment is None:
        return None
    
    if full_path:
        full_path.extend(return_segment[1:])
    else:
        full_path.extend(return_segment)
    
    return full_path


# ==================== PLAN HANDLERS ====================

def handle_analyze_result(payload):
    """Create plan based on analysis."""
    if not payload.get('requires_adaptation'):
        client.publish(Topics.PLAN_RESULT, {'action': 'continue', 'details': None})
        print("[Plan] No adaptation needed, continue")
        return
    
    adaptation_type = payload.get('adaptation_type')
    monitoring_data = payload.get('monitoring_data', {})
    knowledge = monitoring_data.get('knowledge', {})
    grid = monitoring_data.get('grid', {})
    
    if adaptation_type == 'start_mission':
        plan_new_mission(knowledge, grid)
    elif adaptation_type == 'replan_path':
        plan_replan(knowledge, grid)
    elif adaptation_type == 'deliver_order':
        plan_delivery(knowledge)
    elif adaptation_type == 'end_mission':
        client.publish(Topics.PLAN_RESULT, {'action': 'end_mission', 'details': None})
        print("[Plan] End mission")
    else:
        client.publish(Topics.PLAN_RESULT, {'action': 'continue', 'details': None})


def plan_new_mission(knowledge, grid):
    orders = knowledge.get('pending_orders', [])[:knowledge.get('max_capacity', 3)]
    
    if not orders:
        client.publish(Topics.PLAN_RESULT, {'action': 'continue', 'details': None})
        return
    
    delivery_locations = [o['delivery_location'] for o in orders]
    base = knowledge.get('base_location', [1, 1])
    
    sequence = plan_delivery_sequence(grid, base, delivery_locations, base)
    full_path = create_full_path(grid, base, sequence, base)
    
    if full_path is None:
        client.publish(Topics.PLAN_RESULT, {'action': 'continue', 'details': None})
        return
    
    client.publish(Topics.PLAN_RESULT, {
        'action': 'start_mission',
        'details': {
            'orders_to_load': orders,
            'delivery_sequence': sequence,
            'full_path': full_path
        }
    })
    print(f"[Plan] New mission with {len(orders)} orders")


def plan_replan(knowledge, grid):
    robot_pos = knowledge.get('robot_position', [1, 1])
    base = knowledge.get('base_location', [1, 1])
    remaining = [o['delivery_location'] for o in knowledge.get('loaded_orders', [])]
    
    if not remaining:
        new_path = find_path(grid, robot_pos, base)
        new_sequence = []
    else:
        new_sequence = plan_delivery_sequence(grid, robot_pos, remaining, base)
        new_path = create_full_path(grid, robot_pos, new_sequence, base)
    
    if new_path is None:
        client.publish(Topics.PLAN_RESULT, {
            'action': 'wait',
            'details': {'reason': 'no_valid_path'}
        })
        print("[Plan] No valid path, wait")
        return
    
    client.publish(Topics.PLAN_RESULT, {
        'action': 'replan',
        'details': {
            'new_path': new_path,
            'new_sequence': new_sequence
        }
    })
    print(f"[Plan] Replanned, path length: {len(new_path)}")


def plan_delivery(knowledge):
    robot_pos = knowledge.get('robot_position')
    
    for order in knowledge.get('loaded_orders', []):
        if order['delivery_location'] == robot_pos:
            client.publish(Topics.PLAN_RESULT, {
                'action': 'deliver',
                'details': {'order': order}
            })
            print(f"[Plan] Deliver order {order['order_id']}")
            return
    
    client.publish(Topics.PLAN_RESULT, {'action': 'continue', 'details': None})


if __name__ == '__main__':
    print("[Plan] Service starting...")
    
    client = MQTTClient('plan-service')
    client.connect()
    
    client.subscribe(Topics.ANALYZE_RESULT, handle_analyze_result)
    
    print("[Plan] Service ready, waiting for messages...")
    client.loop_forever()