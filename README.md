# Autonomous Delivery Robot 🤖

A self-adaptive autonomous delivery robot simulation implementing the **MAPE-K (Monitor, Analyze, Plan, Execute, Knowledge)** architecture for autonomic computing.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

![Autonomous Delivery Robot](assets/autonomous2.png)

## 📋 Table of Contents


- [Overview](#🎯-overview)
- [Features](#✨-features)
- [Architecture](#🏗️-architecture)
- [Project Structure](#📁-project-structure)
- [Installation](#🚀-installation)
- [Usage](#🎮-usage)
- [MAPE-K Components](#🔧-mape-k-components)
- [Metrics & Config](#📊-metrics)
- [Contributors](#👥-developed-by)

## 🎯 Overview

This project simulates an autonomous delivery robot operating in a 2D grid environment (22x15). The robot picks up orders from a supermarket and delivers them to houses while adapting to dynamic obstacles in real-time.

The system demonstrates key concepts of **self-adaptive systems**:
- Real-time monitoring of the environment
- Analysis of situations requiring adaptation
- Dynamic path planning using A* algorithm
- Execution of movement and delivery actions
- Knowledge base maintaining system state

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

## 🏗️ Architecture

The system uses a **centralized MAPE-K loop** architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Autonomic Manager                            │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Monitor  │─►│ Analyze  │─►│   Plan   │─►│ Execute  │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │             │             │             │                   │
│       │ writes      │ reads       │ reads       │ updates           │
│       ▼             ▼             ▼             ▼                   │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                        Knowledge                             │   │
│  │                    (pure data storage)                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│       ▲                           ▲             │                   │
│       │ sensors                   │ pathfinding │ effectors         │
└───────┼───────────────────────────┼─────────────┼───────────────────┘
        │                           │             │
        │                           │             ▼
┌───────┴───────────────────────────┴─────────────┴───────────────────┐
│                           Environment                               │
│                       (Grid World + Robot)                          │
└─────────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
autonomous-delivery-robot/
├── assets/                      # Icon images
│   ├── robot.png
│   ├── supermarket.png
│   ├── house.png
│   ├── pending.png
│   ├── tree.png
│   └── roadblock.png
├── environment/                 # Environment components
│   ├── __init__.py
│   ├── grid_world.py           # 2D grid map (22x15)
│   └── robot.py                # Robot entity
├── mape_k/                      # MAPE-K components
│   ├── __init__.py
│   ├── knowledge.py            # Knowledge base
│   ├── monitor.py              # Monitor component
│   ├── analyze.py              # Analyze component
│   ├── plan.py                 # Plan component
│   └── execute.py              # Execute component
├── utils/                       # Utilities
│   ├── __init__.py
│   └── pathfinding.py          # A* algorithm & optimal delivery planner
├── web/                         # Web interface
│   ├── app.py                  # Flask + Socket.IO server
│   └── templates/
│       └── index.html          # Web UI
├── requirements.txt             # Dependencies
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 🚀 Installation

### Prerequisites
- Docker
- Docker Compose

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/autonomous-delivery-robot.git
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

4. **Stop the container**
   ```bash
   docker-compose down
   ```

### Alternative: Run with Docker directly
```bash
# Build the image
docker build -t delivery-robot .

# Run the container
docker run -p 5000:5000 delivery-robot
```

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

## 🔧 MAPE-K Components

### Monitor (`mape_k/monitor.py`)
- Collects sensor data: robot position, obstacles, orders
- Detects path blockages
- Tracks environmental changes

### Analyze (`mape_k/analyze.py`)
- Evaluates if adaptation is needed
- Detects mission triggers (capacity/timeout)
- Identifies stuck states
- Determines replanning requirements

### Plan (`mape_k/plan.py`)
- Creates optimal delivery sequences
- Generates paths using A* algorithm
- Handles replanning when blocked

### Execute (`mape_k/execute.py`)
- Issues movement commands
- Handles order loading/delivery
- Manages mission lifecycle

### Knowledge (`mape_k/knowledge.py`)
- Stores map, robot state, orders
- Maintains delivery sequence and original last delivery
- Tracks metrics (distance, time, replans)

## 📊 Metrics

The system tracks:
- **Total Deliveries**: Number of completed deliveries
- **Total Distance**: Cells traveled by the robot
- **Replans**: Number of path recalculations
- **Average Delivery Time**: Mean time per delivery

## 🛠️ Configuration

Key parameters in the code:

| Parameter | Location | Default | Description |
|-----------|----------|---------|-------------|
| Grid size | `grid_world.py` | 22x15 | Map dimensions |
| Max capacity | `app.py` | 3 | Orders per mission |
| Mission timeout | `knowledge.py` | 30s | Auto-start timer |
| Robot speed | `app.py` | 0.4s | Step delay |

## 👥 Developed by

- [Mete Harun Akcay](https://github.com/meteharun)
- [Thanh Phuc Tran](https://github.com/phuc-tr)
- [Pragati Manandhar](https://github.com/mdhrpragati)

## 🙏 Acknowledgements

This project was developed for the **Software Engineering for Autonomous Systems (SE4AS)** course, University of L'Aquila, Fall Semester 2025–2026.
