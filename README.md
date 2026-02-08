# Autonomous Delivery Robot 🤖

A self-adaptive autonomous delivery robot simulation implementing the **MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge)** architecture as a microservices system with MQTT-based communication.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![MQTT](https://img.shields.io/badge/MQTT-Mosquitto-purple.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

![Autonomous Delivery Robot](assets/autonomous2.png)

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Usage](#-usage)
- [Configuration](#-configuration)
- [MAPE-K Components](#-mape-k-components)
- [MQTT Topics](#-mqtt-topics)
- [Metrics](#-metrics)
- [Contributors](#-developed-by)

## 🎯 Overview

This project simulates an autonomous delivery robot operating in a 2D grid environment (22x15). The robot picks up orders from a supermarket and delivers them to houses while adapting to dynamic obstacles in real-time.

The system demonstrates key concepts of **self-adaptive systems**:
- Real-time monitoring of the environment
- Analysis of situations requiring adaptation
- Dynamic path planning using A* algorithm
- Execution of movement and delivery actions
- Knowledge base maintaining system state

**Key architectural feature**: Each MAPE-K component runs as an independent Docker container with **no shared code**. Services communicate via MQTT and read configuration from a shared `config.json` file. This enables **true runtime replacement** of any component without affecting others.

## ✨ Features

- **Autonomous Navigation**: A* pathfinding with optimal delivery sequence (tries all permutations for ≤5 deliveries)
- **Dynamic Adaptation**: Real-time replanning when obstacles appear/disappear
- **Interactive Environment**: Click to add orders or place/remove roadblocks
- **Visual Feedback**: 
  - Delivery order numbers (1, 2, 3) showing priority
  - Pending order indicators
  - Path visualization with color coding:
    - **Blue line**: Delivery path (Base → Houses)
    - **Red line**: Return path (Last house → Base)
  - Stuck state detection
- **Mission Management**:
  - Auto-start after 3 orders OR 30-second timeout
  - Capacity-based loading (max 3 orders)
- **Metrics Tracking**: Distance traveled, deliveries completed, replans count, average delivery time
- **True Microservices**: Each service is fully standalone with no shared code dependencies


### MAPE-K Message Flow

```
Web triggers ──► mape/monitor/request
                        │
                        ▼
              Monitor publishes ──► mape/monitor/result
                                           │
                                           ▼
                                 Analyze publishes ──► mape/analyze/result
                                                              │
                                                              ▼
                                                    Plan publishes ──► mape/plan/result
                                                                              │
                                                                              ▼
                                                                    Execute commands
                                                                    environment & knowledge
```

## 📁 Project Structure

```
autonomous-delivery-robot/
├── config.json                  # Shared configuration (topics, settings)
├── docker-compose.yml
├── mosquitto.conf
├── assets/                      # Icon images
│   ├── robot.png
│   ├── supermarket.png
│   ├── house.png
│   ├── pending.png
│   ├── tree.png
│   └── roadblock.png
└── services/
    ├── knowledge/              
    │   ├── Dockerfile
    │   └── service.py
    ├── environment/           
    │   ├── Dockerfile
    │   └── service.py
    ├── monitor/                 
    │   ├── Dockerfile
    │   └── service.py
    ├── analyze/                 
    │   ├── Dockerfile
    │   └── service.py
    ├── plan/                    
    │   ├── Dockerfile
    │   └── service.py
    ├── execute/                 
    │   ├── Dockerfile
    │   └── service.py
    └── web/                    
        ├── Dockerfile
        ├── service.py
        └── templates/
            └── index.html
```

**Note**: There is no `shared/` folder. Each service is completely standalone and reads configuration from `config.json`.

## 🚀 Installation

### Prerequisites
- Docker
- Docker Compose

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/meteharun/autonomous-delivery-robot.git
   cd autonomous-delivery-robot
   ```

2. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Open in browser**
   ```
   http://localhost:5000
   ```

4. **Stop the containers**
   ```bash
   docker-compose down
   ```

### Runtime Component Replacement

Each service is fully standalone with no shared code. To replace a component:

```bash
# Stop only the plan service
docker-compose stop plan

# Modify services/plan/service.py (e.g., change algorithm)

# Rebuild and restart only the plan service
docker-compose up --build plan
```

The other services continue running and will automatically use the updated Plan service when it reconnects to MQTT.

## 🎮 Usage

### Controls

| Action | How To |
|--------|--------|
| **Add delivery order** | Click on a house (building icon) |
| **Add roadblock** | Click on an empty road cell |
| **Remove roadblock** | Click on an existing roadblock |
| **Reset simulation** | Click the Reset button |

### Mission Rules

- **Capacity**: Robot can carry up to 3 orders at once
- **Auto-start**: Mission begins when:
  - 3 orders are pending, OR
  - 30 seconds have passed since first order
- **Delivery order**: Optimal route algorithm (brute-force for ≤5 orders, nearest-neighbor for more)
- **Replanning**: Robot automatically recalculates path when:
  - A roadblock is added in its path
  - A roadblock is removed (may find shorter path)

### Visual Indicators

| Symbol | Meaning |
|--------|---------|
| 🤖 Robot icon | Current robot position |
| 🏪 Supermarket (2x2) | Base station - robot starts/returns here |
| 🏠 House | Delivery location |
| 📦 Pending icon | Order waiting to be picked up |
| 1️⃣ 2️⃣ 3️⃣ Numbers | Delivery sequence order |
| 🌳 Tree | Static obstacle (cannot be removed) |
| 🚧 Roadblock | Dynamic obstacle (can be toggled) |
| 🔵 Blue line | Delivery path (Base → Houses) |
| 🔴 Red line | Return path (Last house → Base) |
| ⚠️ STUCK | Robot has no valid path |

## ⚙️ Configuration

All services read from `config.json`:

```json
{
  "mqtt": {
    "broker": "mqtt",
    "port": 1883
  },
  "topics": {
    "system_init": "system/init",
    "system_reset": "system/reset",
    "monitor_request": "mape/monitor/request",
    "monitor_result": "mape/monitor/result",
    "analyze_result": "mape/analyze/result",
    "plan_result": "mape/plan/result",
    "knowledge_update": "knowledge/update",
    "knowledge_set": "knowledge/set",
    "environment_update": "environment/update",
    ...
  },
  "robot": {
    "max_capacity": 3,
    "mission_timeout": 30,
    "base_location": [1, 1]
  },
  "grid": {
    "width": 22,
    "height": 15
  }
}
```

| Parameter | Description |
|-----------|-------------|
| `mqtt.broker` | MQTT broker hostname |
| `mqtt.port` | MQTT broker port |
| `topics.*` | MQTT topic names for all communication |
| `robot.max_capacity` | Maximum orders per mission |
| `robot.mission_timeout` | Seconds before auto-start |
| `robot.base_location` | Starting position |
| `grid.width/height` | Grid dimensions |

## 🔧 MAPE-K Components

Each component runs as an independent Docker container with no shared code:

### Knowledge (`services/knowledge/service.py`)
- Subscribes to: `system/init`, `system/reset`, `user/add_order`, `knowledge/set`
- Publishes to: `knowledge/update`
- Stores system state: orders, plan, metrics

### Monitor (`services/monitor/service.py`)
- Subscribes to: `knowledge/update`, `environment/update`, `mape/monitor/request`
- Publishes to: `mape/monitor/result`
- Collects sensor data, detects path blockages

### Analyze (`services/analyze/service.py`)
- Subscribes to: `mape/monitor/result`
- Publishes to: `mape/analyze/result`
- Evaluates adaptation needs, applies rules

### Plan (`services/plan/service.py`)
- Subscribes to: `mape/analyze/result`
- Publishes to: `mape/plan/result`
- A* pathfinding, optimal delivery sequences

### Execute (`services/execute/service.py`)
- Subscribes to: `mape/plan/result`, `knowledge/update`, `environment/update`
- Publishes to: `knowledge/set`, `environment/*` commands
- Commands robot, updates state

### Environment (`services/environment/service.py`)
- Subscribes to: `system/init`, `system/reset`, `user/toggle_obstacle`, `environment/*`
- Publishes to: `environment/update`
- Manages Grid and Robot state

## 📡 MQTT Topics

| Topic | Publisher | Subscribers | Purpose |
|-------|-----------|-------------|---------|
| `system/init` | Web | Knowledge, Environment | Initialize system |
| `system/reset` | Web | All services | Reset simulation |
| `user/add_order` | Web | Knowledge | Add delivery order |
| `user/toggle_obstacle` | Web | Environment | Add/remove roadblock |
| `mape/monitor/request` | Web | Monitor | Trigger monitoring cycle |
| `mape/monitor/result` | Monitor | Analyze | Sensor data & conditions |
| `mape/analyze/result` | Analyze | Plan | Adaptation decision |
| `mape/plan/result` | Plan | Execute | Action with path/sequence |
| `knowledge/update` | Knowledge | Monitor, Execute, Web | Current system state |
| `knowledge/set` | Execute | Knowledge | Update state fields |
| `environment/update` | Environment | Monitor, Execute, Web | Grid and robot state |
| `environment/move_robot` | Execute | Environment | Move command |
| `environment/load_order` | Execute | Environment | Load order command |
| `environment/deliver_order` | Execute | Environment | Deliver command |

## 📊 Metrics

The system tracks:
- **Total Deliveries**: Number of completed deliveries
- **Total Distance**: Cells traveled by the robot
- **Replans**: Number of path recalculations
- **Average Delivery Time**: Mean time per delivery

## 👥 Developed by

- [Mete Harun Akcay](https://github.com/meteharun)
- [Thanh Phuc Tran](https://github.com/phuc-tr)
- [Pragati Manandhar](https://github.com/mdhrpragati)

## 🙏 Acknowledgements

This project was developed for the **Software Engineering for Autonomous Systems (SE4AS)** course, University of L'Aquila, Fall Semester 2025–2026.
