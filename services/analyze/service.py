"""
Analyze Service - Analyzes monitoring results and decides adaptation.
Listens to: MONITOR_RESULT
Publishes to: ANALYZE_RESULT
"""
import sys

sys.path.insert(0, '/app')
from shared.mqtt_client import MQTTClient, Topics


def handle_monitor_result(payload):
    """Analyze monitoring results and publish analysis."""
    knowledge = payload.get('knowledge', {})
    
    analysis = {
        'requires_adaptation': False,
        'adaptation_type': None,
        'reason': None,
        'monitoring_data': payload
    }
    
    # === RULE-BASED ANALYSIS ===
    
    # Rule 1: Check if new mission should start
    if payload.get('needs_new_mission') and not knowledge.get('mission_in_progress'):
        analysis['requires_adaptation'] = True
        analysis['adaptation_type'] = 'start_mission'
        analysis['reason'] = 'Capacity full or timeout reached'
        client.publish(Topics.ANALYZE_RESULT, analysis)
        print(f"[Analyze] Decision: start_mission")
        return
    
    # Rule 2: Check if path is blocked
    if payload.get('path_blocked'):
        analysis['requires_adaptation'] = True
        analysis['adaptation_type'] = 'replan_path'
        analysis['reason'] = 'Current path blocked by dynamic obstacle'
        client.publish(Topics.ANALYZE_RESULT, analysis)
        print(f"[Analyze] Decision: replan_path (blocked)")
        return
    
    # Rule 3: Check if obstacle was removed
    if payload.get('obstacle_removed') and knowledge.get('mission_in_progress'):
        analysis['requires_adaptation'] = True
        analysis['adaptation_type'] = 'replan_path'
        if knowledge.get('is_stuck'):
            analysis['reason'] = 'Obstacle removed - attempting to resume'
        else:
            analysis['reason'] = 'Obstacle removed - recalculating optimal path'
        client.publish(Topics.ANALYZE_RESULT, analysis)
        print(f"[Analyze] Decision: replan_path (obstacle removed)")
        return
    
    # Rule 4: Check if at delivery location
    if payload.get('at_delivery_location') and knowledge.get('loaded_orders'):
        analysis['requires_adaptation'] = True
        analysis['adaptation_type'] = 'deliver_order'
        analysis['reason'] = 'Reached delivery location'
        client.publish(Topics.ANALYZE_RESULT, analysis)
        print(f"[Analyze] Decision: deliver_order")
        return
    
    # Rule 5: Check if mission complete
    if (knowledge.get('mission_in_progress') and 
        payload.get('at_base') and 
        len(knowledge.get('loaded_orders', [])) == 0):
        analysis['requires_adaptation'] = True
        analysis['adaptation_type'] = 'end_mission'
        analysis['reason'] = 'All deliveries completed, returned to base'
        client.publish(Topics.ANALYZE_RESULT, analysis)
        print(f"[Analyze] Decision: end_mission")
        return
    
    # No adaptation needed - continue
    client.publish(Topics.ANALYZE_RESULT, analysis)
    print(f"[Analyze] Decision: continue")


if __name__ == '__main__':
    print("[Analyze] Service starting...")
    
    client = MQTTClient('analyze-service')
    client.connect()
    
    # Subscribe to monitor results
    client.subscribe(Topics.MONITOR_RESULT, handle_monitor_result)
    
    print("[Analyze] Service ready, waiting for messages...")
    client.loop_forever()