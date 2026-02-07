"""
Plan Service - Creates plans using A* pathfinding.
"""
import paho.mqtt.client as mqtt
import json
import time
import uuid
import os
import heapq
from itertools import permutations

# Load config
with open('/app/config.json') as f:
    CONFIG = json.load(f)

BROKER = os.environ.get('MQTT_BROKER', CONFIG['mqtt']['broker'])
PORT = CONFIG['mqtt']['port']
TOPICS = CONFIG['topics']

OBSTACLE = 1
client = None


# ========== A* PATHFINDING ==========

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def get_neighbors(grid, pos):
    row, col = pos
    height = len(grid['grid'])
    width = len(grid['grid'][0])
    
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        r, c = row + dr, col + dc
        if 0 <= r < height and 0 <= c < width:
            if grid['grid'][r][c] != OBSTACLE:
                if [r, c] not in grid.get('dynamic_obstacles', []):
                    yield (r, c)


def find_path(grid, start, goal):
    start = tuple(start)
    goal = tuple(goal)
    
    if start == goal:
        return [list(start)]
    
    if grid['grid'][goal[0]][goal[1]] == OBSTACLE:
        return None
    if list(goal) in grid.get('dynamic_obstacles', []):
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
                counter += 1
                f = len(new_path) - 1 + heuristic(neighbor, goal)
                heapq.heappush(frontier, (f, counter, neighbor, new_path))
    
    return None


def calc_distance(grid, p1, p2):
    path = find_path(grid, p1, p2)
    return len(path) - 1 if path else float('inf')


def plan_sequence(grid, start, deliveries, base):
    if not deliveries:
        return []
    if len(deliveries) == 1:
        return [deliveries[0]]
    
    if len(deliveries) <= 5:
        return optimal_sequence(grid, start, deliveries, base)
    return nearest_neighbor(grid, start, deliveries)


def optimal_sequence(grid, start, deliveries, base):
    start = tuple(start)
    base = tuple(base)
    locs = [tuple(d) for d in deliveries]
    
    best_seq, best_dist = None, float('inf')
    
    for perm in permutations(locs):
        dist, current = 0, start
        valid = True
        for loc in perm:
            d = calc_distance(grid, current, loc)
            if d == float('inf'):
                valid = False
                break
            dist += d
            current = loc
        if valid:
            d = calc_distance(grid, current, base)
            if d != float('inf'):
                dist += d
                if dist < best_dist:
                    best_dist, best_seq = dist, list(perm)
    
    if best_seq:
        return [list(p) for p in best_seq]
    return nearest_neighbor(grid, start, deliveries)


def nearest_neighbor(grid, start, deliveries):
    seq = []
    remaining = [list(d) for d in deliveries]
    current = list(start)
    
    while remaining:
        nearest, min_d = None, float('inf')
        for loc in remaining:
            d = calc_distance(grid, current, loc)
            if d < min_d:
                min_d, nearest = d, loc
        if not nearest:
            break
        seq.append(nearest)
        remaining.remove(nearest)
        current = nearest
    
    return seq


def create_full_path(grid, start, sequence, base):
    path = []
    current = start
    
    for loc in sequence:
        segment = find_path(grid, current, loc)
        if not segment:
            return None
        path.extend(segment[1:] if path else segment)
        current = loc
    
    segment = find_path(grid, current, base)
    if not segment:
        return None
    path.extend(segment[1:] if path else segment)
    
    return path


def handle_message(client_obj, userdata, msg):
    global client
    
    try:
        topic = msg.topic
        payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        
        if topic == TOPICS['analyze_result']:
            if not payload.get('requires_adaptation'):
                client.publish(TOPICS['plan_result'], json.dumps({'action': 'continue'}))
                print("[Plan] No adaptation needed")
                return
            
            action = payload.get('adaptation_type')
            knowledge = payload.get('knowledge', {})
            grid = payload.get('grid', {})
            
            if action == 'start_mission':
                plan_start_mission(knowledge, grid)
            elif action == 'replan':
                plan_replan(knowledge, grid)
            elif action == 'deliver':
                plan_deliver(knowledge)
            elif action == 'end_mission':
                client.publish(TOPICS['plan_result'], json.dumps({'action': 'end_mission'}))
                print("[Plan] End mission")
            else:
                client.publish(TOPICS['plan_result'], json.dumps({'action': 'continue'}))
    
    except Exception as e:
        print(f"[Plan] Error: {e}")


def plan_start_mission(knowledge, grid):
    global client
    
    orders = knowledge.get('pending_orders', [])[:knowledge.get('max_capacity', 3)]
    if not orders or not grid:
        client.publish(TOPICS['plan_result'], json.dumps({'action': 'continue'}))
        return
    
    base = knowledge.get('base_location', [1, 1])
    deliveries = [o['delivery_location'] for o in orders]
    
    sequence = plan_sequence(grid, base, deliveries, base)
    path = create_full_path(grid, base, sequence, base)
    
    if not path:
        client.publish(TOPICS['plan_result'], json.dumps({'action': 'continue'}))
        return
    
    client.publish(TOPICS['plan_result'], json.dumps({
        'action': 'start_mission',
        'orders': orders,
        'sequence': sequence,
        'path': path
    }))
    print(f"[Plan] Start mission: {len(orders)} orders, path: {len(path)} steps")


def plan_replan(knowledge, grid):
    global client
    
    pos = knowledge.get('robot_position', [1, 1])
    base = knowledge.get('base_location', [1, 1])
    loaded = knowledge.get('loaded_orders', [])
    
    if not loaded:
        path = find_path(grid, pos, base)
        sequence = []
    else:
        deliveries = [o['delivery_location'] for o in loaded]
        sequence = plan_sequence(grid, pos, deliveries, base)
        path = create_full_path(grid, pos, sequence, base)
    
    if not path:
        client.publish(TOPICS['plan_result'], json.dumps({'action': 'wait', 'reason': 'no_path'}))
        print("[Plan] No path - wait")
        return
    
    client.publish(TOPICS['plan_result'], json.dumps({
        'action': 'replan',
        'path': path,
        'sequence': sequence
    }))
    print(f"[Plan] Replanned: {len(path)} steps")


def plan_deliver(knowledge):
    global client
    
    pos = knowledge.get('robot_position')
    for order in knowledge.get('loaded_orders', []):
        if order['delivery_location'] == pos:
            client.publish(TOPICS['plan_result'], json.dumps({
                'action': 'deliver',
                'order': order
            }))
            print(f"[Plan] Deliver {order['order_id']}")
            return
    
    client.publish(TOPICS['plan_result'], json.dumps({'action': 'continue'}))


def on_connect(client_obj, userdata, flags, rc):
    print("[Plan] Connected to MQTT")
    client_obj.subscribe(TOPICS['analyze_result'])


if __name__ == '__main__':
    print("[Plan] Starting...")
    
    client = mqtt.Client(client_id=f"plan-{uuid.uuid4().hex[:8]}")
    client.on_connect = on_connect
    client.on_message = handle_message
    
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            break
        except:
            print("[Plan] Waiting for MQTT...")
            time.sleep(2)
    
    print("[Plan] Ready")
    client.loop_forever()