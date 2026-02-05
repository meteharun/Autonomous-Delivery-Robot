from mape_k.knowledge import Knowledge
from typing import Dict, Any, Set

class Monitor:
    """
    Monitor component of MAPE-K loop.
    Reads sensor data from Environment (grid_world, robot) and updates Knowledge.
    """
    
    def __init__(self, knowledge: Knowledge, grid_world, robot):
        self.knowledge = knowledge
        self.grid_world = grid_world  # Sensor access to environment
        self.robot = robot  # Sensor access to robot
        self.previous_obstacles: Set[tuple] = set()
    
    def collect_data(self) -> Dict[str, Any]:
        """
        Collect data from environment sensors and update knowledge base.
        """
        # READ from environment sensors
        robot_position = self.robot.get_position()
        loaded_orders = self.robot.get_loaded_orders()
        capacity_status = self.robot.get_capacity_status()
        is_at_base = self.robot.is_at_base
        dynamic_obstacles = list(self.grid_world.dynamic_obstacles)
        
        # WRITE to knowledge base
        self.knowledge.robot_position = robot_position
        self.knowledge.robot_is_at_base = is_at_base
        self.knowledge.loaded_orders = loaded_orders
        self.knowledge.known_blockages = dynamic_obstacles
        
        # Return sensor data for Analyze
        sensor_data = {
            'robot_position': robot_position,
            'loaded_orders': loaded_orders,
            'capacity_status': capacity_status,
            'is_at_base': is_at_base,
            'pending_orders_count': len(self.knowledge.pending_orders),
            'dynamic_obstacles': dynamic_obstacles,
            'mission_in_progress': self.knowledge.mission_in_progress
        }
        
        return sensor_data
    
    def check_mission_trigger(self) -> bool:
        """Check if conditions are met to start a delivery mission."""
        return self.knowledge.should_start_mission()
    
    def check_path_validity(self) -> bool:
        """Check if the current path is still valid."""
        if not self.knowledge.current_plan:
            return False
        
        return self.knowledge.is_path_blocked(self.grid_world)
    
    def check_obstacle_removed(self) -> bool:
        """Check if any dynamic obstacle was removed since last check."""
        current_obstacles = set(self.grid_world.dynamic_obstacles)
        removed = self.previous_obstacles - current_obstacles
        return len(removed) > 0
    
    def monitor_step(self) -> Dict[str, Any]:
        """Execute one monitoring cycle."""
        sensor_data = self.collect_data()
        
        obstacle_removed = self.check_obstacle_removed()
        
        # Update previous obstacles for next cycle
        self.previous_obstacles = set(self.grid_world.dynamic_obstacles)
        
        monitoring_results = {
            'sensor_data': sensor_data,
            'needs_new_mission': self.check_mission_trigger(),
            'path_blocked': self.check_path_validity(),
            'obstacle_removed': obstacle_removed,
            'at_delivery_location': False,
            'at_base': sensor_data['is_at_base']
        }
        
        # Check if at a delivery location
        robot_pos = sensor_data['robot_position']
        for order in self.knowledge.loaded_orders:
            if order.delivery_location == robot_pos:
                monitoring_results['at_delivery_location'] = True
                break
        
        return monitoring_results