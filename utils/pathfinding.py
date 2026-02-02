import heapq
from typing import Tuple, List, Optional, Set
from itertools import permutations
import math

class AStar:
    """
    A* pathfinding algorithm for grid-based navigation.
    """
    
    @staticmethod
    def heuristic(a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Manhattan distance heuristic."""
        return abs(a[0] - b[0]) + abs(a[1] - b[1])
    
    @staticmethod
    def find_path(grid_world, start: Tuple[int, int], 
                  goal: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Find the shortest path from start to goal using A*.
        
        Returns:
            List of positions from start to goal, or None if no path exists.
        """
        if start == goal:
            return [start]
        
        if not grid_world.is_valid_position(goal):
            return None
        
        # Priority queue: (f_score, counter, position, path)
        counter = 0
        frontier = [(0, counter, start, [start])]
        visited: Set[Tuple[int, int]] = set()
        
        while frontier:
            _, _, current, path = heapq.heappop(frontier)
            
            if current in visited:
                continue
            
            visited.add(current)
            
            if current == goal:
                return path
            
            # Explore neighbors
            for neighbor in grid_world.get_neighbors(current):
                if neighbor not in visited:
                    new_path = path + [neighbor]
                    g_score = len(new_path) - 1
                    h_score = AStar.heuristic(neighbor, goal)
                    f_score = g_score + h_score
                    
                    counter += 1
                    heapq.heappush(frontier, (f_score, counter, neighbor, new_path))
        
        return None  # No path found


class DeliveryPlanner:
    """
    Plans the sequence of deliveries to minimize total travel distance.
    """
    
    @staticmethod
    def calculate_distance(grid_world, pos1: Tuple[int, int], 
                          pos2: Tuple[int, int]) -> float:
        """Calculate path distance between two positions."""
        path = AStar.find_path(grid_world, pos1, pos2)
        return len(path) - 1 if path else float('inf')
    
    @staticmethod
    def plan_delivery_sequence(grid_world, start_pos: Tuple[int, int],
                              delivery_locations: List[Tuple[int, int]],
                              return_to_base: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Plan the optimal sequence of deliveries.
        
        For small numbers of deliveries (≤5), uses brute force to find optimal route.
        For larger numbers, falls back to nearest-neighbor heuristic.
        
        Returns:
            Ordered list of delivery locations.
        """
        if not delivery_locations:
            return []
        
        if len(delivery_locations) == 1:
            return delivery_locations.copy()
        
        # For small number of deliveries, find optimal route by trying all permutations
        if len(delivery_locations) <= 5:
            return DeliveryPlanner._find_optimal_sequence(
                grid_world, start_pos, delivery_locations, return_to_base
            )
        
        # For larger numbers, use nearest-neighbor heuristic
        return DeliveryPlanner._nearest_neighbor_sequence(
            grid_world, start_pos, delivery_locations
        )
    
    @staticmethod
    def _find_optimal_sequence(grid_world, start_pos: Tuple[int, int],
                               delivery_locations: List[Tuple[int, int]],
                               return_to_base: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        Find the optimal delivery sequence by evaluating all permutations.
        
        When total distances are equal, prioritizes sequences where:
        - Deliveries closer to start are visited first (minimizes sum of delivery times)
        """
        # Pre-calculate distances between all relevant points
        all_points = [start_pos] + delivery_locations + [return_to_base]
        distance_cache = {}
        
        for i, p1 in enumerate(all_points):
            for j, p2 in enumerate(all_points):
                if i != j and (p1, p2) not in distance_cache:
                    dist = DeliveryPlanner.calculate_distance(grid_world, p1, p2)
                    distance_cache[(p1, p2)] = dist
                    distance_cache[(p2, p1)] = dist
        
        best_sequence = None
        best_total_distance = float('inf')
        best_sum_delivery_times = float('inf')
        
        # Try all permutations
        for perm in permutations(delivery_locations):
            total_distance = 0
            sum_delivery_times = 0  # Sum of time to reach each delivery point
            cumulative_distance = 0
            current = start_pos
            valid = True
            
            # Calculate distance for this sequence
            for delivery in perm:
                dist = distance_cache.get((current, delivery), float('inf'))
                if dist == float('inf'):
                    valid = False
                    break
                cumulative_distance += dist
                sum_delivery_times += cumulative_distance  # Time to reach this delivery
                total_distance += dist
                current = delivery
            
            # Add return to base distance
            if valid:
                return_dist = distance_cache.get((current, return_to_base), float('inf'))
                if return_dist == float('inf'):
                    valid = False
                else:
                    total_distance += return_dist
            
            # Check if this is the best so far
            # Prefer: 1) shorter total distance, 2) lower sum of delivery times (closer first)
            if valid:
                is_better = False
                if total_distance < best_total_distance:
                    is_better = True
                elif total_distance == best_total_distance and sum_delivery_times < best_sum_delivery_times:
                    is_better = True
                
                if is_better:
                    best_total_distance = total_distance
                    best_sum_delivery_times = sum_delivery_times
                    best_sequence = list(perm)
        
        if best_sequence is None:
            # Fallback to nearest neighbor if no valid sequence found
            return DeliveryPlanner._nearest_neighbor_sequence(
                grid_world, start_pos, delivery_locations
            )
        
        print(f"Optimal route found: {best_sequence} (total distance: {best_total_distance}, sum delivery times: {best_sum_delivery_times})")
        return best_sequence
    
    @staticmethod
    def _nearest_neighbor_sequence(grid_world, start_pos: Tuple[int, int],
                                   delivery_locations: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        Plan delivery sequence using nearest-neighbor heuristic.
        Used as fallback for large numbers of deliveries.
        """
        sequence = []
        remaining = delivery_locations.copy()
        current_pos = start_pos
        
        while remaining:
            # Find nearest unvisited delivery location
            nearest = None
            min_distance = float('inf')
            
            for location in remaining:
                distance = DeliveryPlanner.calculate_distance(
                    grid_world, current_pos, location)
                if distance < min_distance:
                    min_distance = distance
                    nearest = location
            
            if nearest is None:
                break
            
            sequence.append(nearest)
            remaining.remove(nearest)
            current_pos = nearest
        
        return sequence
    
    @staticmethod
    def create_full_path(grid_world, start_pos: Tuple[int, int],
                        delivery_sequence: List[Tuple[int, int]],
                        return_to_base: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
        """
        Create the complete path including all deliveries and return to base.
        
        Returns:
            Complete path or None if any segment is unreachable.
        """
        full_path = []
        current_pos = start_pos
        
        for delivery_loc in delivery_sequence:
            segment = AStar.find_path(grid_world, current_pos, delivery_loc)
            if segment is None:
                return None
            
            # Avoid duplicating positions between segments
            if full_path and segment:
                full_path.extend(segment[1:])
            else:
                full_path.extend(segment)
            
            current_pos = delivery_loc
        
        # Return to base
        return_segment = AStar.find_path(grid_world, current_pos, return_to_base)
        if return_segment is None:
            return None
        
        if full_path and return_segment:
            full_path.extend(return_segment[1:])
        else:
            full_path.extend(return_segment)
        
        return full_path