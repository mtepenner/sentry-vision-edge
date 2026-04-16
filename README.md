# 🛡️ Sentry Vision Edge

An intelligent, edge-deployed surveillance and tracking system optimized for NVIDIA Jetson hardware. Sentry Vision Edge integrates real-time object detection using thermal camera streams, a Go-based decision engine for evaluating threat heuristics, and a rich interactive web dashboard. 

## 📑 Table of Contents
- [Features](#-features)
- [Architecture](#-architecture)
- [Technologies Used](#-technologies-used)
- [Installation](#-installation)
- [Usage](#-usage)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features
* **Real-Time Object Detection:** Runs highly optimized, quantized YOLOv8/v10 models using TensorRT.
* **Thermal Vision Integration:** Direct interfacing with FLIR and Seek thermal cameras via V4L2.
* **Behavioral Heuristics:** Advanced Go-based logic to detect loitering and virtual "tripwire" boundary crossings.
* **Automated Tracking:** Implements Simple Online and Realtime Tracking (SORT) and can command pan-tilt motors to keep threats centered.
* **Alert Management:** Automatically triggers notifications via Slack, Telegram, or local alarms.
* **Interactive Command Dashboard:** A React/TypeScript HUD featuring low-latency WebRTC feeds, SVG overlays, and a Perimeter Editor for drawing custom tripwires.

## 🏗️ Architecture
The system operates using a multi-container stack divided into three primary components:
1. **Vision Engine (Python):** Handles the AI inference, bounding box generation, and camera streaming.
2. **Behavioral Brain (Go):** The core decision engine that evaluates track history against security rules (like boundary crossing) and handles alerting.
3. **Command Dashboard (React/TypeScript):** The frontend interface that receives WebSocket metadata from the Go brain and renders active threats alongside the live video feed.

## 🛠️ Technologies Used
* **AI & Vision:** Python, TensorRT, YOLOv8/v10, SORT Tracking
* **Logic & Alerting:** Go (Golang)
* **Frontend:** React, TypeScript, WebRTC, WebSockets
* **Deployment & CI/CD:** Docker, Docker Compose, GitHub Actions
* **Target Hardware:** NVIDIA Jetson (ARM64)

## 💻 Installation

### Prerequisites
* NVIDIA Jetson device (ARM64 architecture).
* Docker and Docker Compose installed.
* Compatible thermal camera (e.g., FLIR/Seek).

### Setup Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/mtepenner/sentry-vision-edge.git
   cd sentry-vision-edge
   ```
2. Ensure your custom TensorRT engine (`custom_sentry_n.engine`) is placed in `vision_engine/models/`.
3. Build and launch the stack using the Jetson-optimized orchestration file:
   ```bash
   docker-compose -f orchestration/docker-compose.jetson.yml up --build -d
   ```

## 🎮 Usage
Once the containers are running:
1. Open your browser and navigate to the Command Dashboard (typically `http://localhost:3000` or the IP of your Jetson device).
2. Use the **Perimeter Editor** to draw virtual tripwires on the map.
3. Monitor the **Threat List** sidebar for active tracks and confidence scores.
4. View the live WebRTC stream with low-latency SVG bounding box overlays.

## 🤝 Contributing
Contributions are welcome! Please ensure that any changes to behavioral logic pass the heuristic filtering tests defined in `.github/workflows/test-behavior-logic.yml`. 

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License
Distributed under the MIT License. See `LICENSE` for more information.
