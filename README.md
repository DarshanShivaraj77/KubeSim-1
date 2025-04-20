# KubeSim - Kubernetes Cluster Simulator 🚀  
**A lightweight Kubernetes-like cluster simulator with scheduling algorithms, auto-scaling, and failure recovery**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.3.x-lightgrey)
![Docker](https://img.shields.io/badge/Docker-API-2496ED)

---

## 🌟 Features  
- **Node management** (Add/remove nodes with custom CPU)  
- **Pod scheduling** (First-Fit, Best-Fit, Worst-Fit algorithms)  
- **Auto-scaling** (Based on CPU threshold)  
- **Failure detection & recovery** (Heartbeat monitoring)  
- **Network policies** (Allow/Deny rules between pods)  
- **Web dashboard** (Real-time cluster visualization)  

---

## 🛠️ Installation  

### Prerequisites  
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y python3 python3-pip docker.io
1. Clone the Repository
bash
git clone https://github.com/DarshanShivaraj77/KubeSim-1.git
cd KubeSim
2. Install Python Dependencies
bash
pip install -r requirements.txt
(or manually install: pip install flask docker python-dotenv)

3. Start Docker Service
bash
sudo systemctl start docker
sudo systemctl enable docker
🚀 Running KubeSim
1. Launch the Application
bash
python3 app.py
2. Access the Web Interface
Open in browser:
🔗 http://localhost:5000

Default Credentials:

Username: admin

Password: admin123

🖥️ Dashboard Overview
Dashboard Preview

Key Sections:
Nodes Tab - View/manage cluster nodes

Pods Tab - Launch pods with CPU requirements

Settings Tab - Configure scheduling algorithms

Network Policies - Define pod communication rules

Testing Tools - Simulate node failures

⚙️ Core Functionality
Scheduling Algorithms
Algorithm	Behavior
First-Fit	Assigns to first node with enough resources
Best-Fit	Assigns to node with smallest remaining capacity
Worst-Fit	Assigns to node with largest remaining capacity
Auto-scaling Rules
python
MIN_NODES = 2       # Minimum cluster size
MAX_NODES = 5       # Maximum cluster size
CPU_THRESHOLD = 0.8 # Scale-up when 80% CPU used
Failure Recovery
Nodes send heartbeats every 5 seconds

Unresponsive nodes are detected after 10 seconds

Pods are automatically rescheduled

🧪 Testing Scenarios
1. Simulate Node Failure
Go to Testing Tools tab

Select a node

Click "Simulate Failure"

2. Trigger Auto-scaling
Launch multiple CPU-intensive pods

Watch new nodes auto-provision at 80% CPU usage

Observe scale-down when utilization drops

3. Test Network Policies
Create "deny" policy between two pods

Verify simulated network isolation

📂 Project Structure
KubeSim/
├── app.py                # Main application (Flask)
├── requirements.txt      # Python dependencies
├── static/               # CSS/JS assets
├── templates/            # HTML templates
│   └── index.html        # Dashboard UI
├── screenshots/          # Documentation images
└── README.md             # This file

📜 License
MIT License
