from flask import Flask, request, render_template, redirect, session, url_for, jsonify
import threading, time, uuid
import docker

app = Flask(__name__)
app.secret_key = 'supersecretkey'
client = docker.from_env()

# In-memory data
nodes = {}
pods = {}
heartbeats = {}
pod_usage = {}  # For pod resource monitoring

node_counter = 1
pod_counter = 1
HEARTBEAT_INTERVAL = 5
NODE_TIMEOUT = 10

# Scheduling algorithm selection
SCHEDULING_ALGORITHM = "best-fit"  # Options: "first-fit", "best-fit", "worst-fit"

# Auto-scaling configuration
AUTO_SCALING_ENABLED = False
MIN_NODES = 2
MAX_NODES = 5
CPU_THRESHOLD = 0.8  # 80% CPU usage triggers scaling

# Network policies (simplified version)
network_policies = {}

# Monitor for failure detection
def monitor_nodes():
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        now = time.time()
        for node_id, data in list(nodes.items()):
            if data["status"] == "healthy" and now - heartbeats.get(node_id, 0) > NODE_TIMEOUT:
                print(f"Node {node_id} marked as unresponsive")
                data["status"] = "unresponsive"
                failed_pods = data["pods"][:]
                data["pods"] = []
                for pid in failed_pods:
                    if pid in pods:
                        cpu = pods[pid]["cpu"]
                        new_pid, new_node = schedule_pod(cpu)
                        if new_pid:
                            print(f"Rescheduling pod {pid} as {new_pid} on {new_node}")
                            pods[new_pid] = {"cpu": cpu, "node_id": new_node}
                            nodes[new_node]["used_cpu"] += cpu
                            nodes[new_node]["pods"].append(new_pid)
                            # Don't delete the old pod to keep history
                            pods[pid]["status"] = "failed"
        
        # Auto-scaling check
        if AUTO_SCALING_ENABLED:
            check_auto_scaling()
        
        # Pod resource usage simulation
        update_pod_usage()

# Simulate pod resource usage
def update_pod_usage():
    import random
    for pod_id, pod_info in list(pods.items()):
        if pod_info.get("status") == "failed":
            continue
            
        if pod_id not in pod_usage:
            # Initialize with a random percentage of its allocated CPU
            pod_usage[pod_id] = {"cpu_usage": random.uniform(0.3, 0.9) * pod_info["cpu"]}
        else:
            # Fluctuate usage slightly to simulate workload changes
            current = pod_usage[pod_id]["cpu_usage"]
            change = random.uniform(-0.1, 0.1) * pod_info["cpu"]
            new_usage = max(0.1, min(pod_info["cpu"], current + change))
            pod_usage[pod_id]["cpu_usage"] = new_usage

# Auto-scaling logic
def check_auto_scaling():
    global node_counter
    
    # Calculate total and used CPU
    healthy_nodes = {nid: info for nid, info in nodes.items() if info["status"] == "healthy"}
    if not healthy_nodes:
        return
        
    total_cpu = sum(node["cpu"] for node in healthy_nodes.values())
    used_cpu = sum(node["used_cpu"] for node in healthy_nodes.values())
    
    if total_cpu == 0:  # Avoid division by zero
        return
        
    usage_ratio = used_cpu / total_cpu
    print(f"Auto-scaling check: {usage_ratio:.2f} ratio, threshold {CPU_THRESHOLD}")
    
    # Scale up if needed
    if usage_ratio > CPU_THRESHOLD and len(nodes) < MAX_NODES:
        print("Scaling up by adding a new node")
        container = client.containers.run("alpine", "sleep 3600", detach=True)
        node_id = f"node-{node_counter}"
        cpu = 4  # Standard size for auto-scaled node
        nodes[node_id] = {
            "cpu": cpu, "used_cpu": 0, "pods": [],
            "status": "healthy", "container_id": container.id,
            "auto_scaled": True
        }
        heartbeats[node_id] = time.time()
        node_counter += 1
    
    # Scale down if possible
    elif usage_ratio < (CPU_THRESHOLD * 0.6) and len(nodes) > MIN_NODES:
        # Find a node with minimal pod usage that was auto-scaled
        for node_id, data in list(nodes.items()):
            if data.get("auto_scaled", False) and len(data["pods"]) == 0:
                # Remove empty auto-scaled node
                print(f"Scaling down by removing node {node_id}")
                try:
                    container = client.containers.get(data["container_id"])
                    container.stop()
                    container.remove()
                except Exception as e:
                    print(f"Error removing container: {e}")
                del nodes[node_id]
                del heartbeats[node_id]
                break

# Start the monitor thread
monitor_thread = threading.Thread(target=monitor_nodes, daemon=True)
monitor_thread.start()

users = {"admin": "admin123"}

@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    if users.get(request.form['username']) == request.form['password']:
        session['user'] = request.form['username']
        return redirect('/dashboard')
    return render_template('index.html', error="Invalid credentials")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    
    # Active pods only for display
    active_pods = {pid: info for pid, info in pods.items() 
                  if info.get("status") != "failed"}
    
    return render_template('index.html', 
                          nodes=nodes, 
                          pods=active_pods, 
                          pod_usage=pod_usage,
                          network_policies=network_policies,
                          current_algorithm=SCHEDULING_ALGORITHM,
                          auto_scaling=AUTO_SCALING_ENABLED, 
                          username=session['user'])

@app.route('/add_node', methods=['POST'])
def add_node():
    global node_counter
    cpu = int(request.form['cpu'])
    
    try:
        container = client.containers.run("alpine", "sleep 3600", detach=True)
        node_id = f"node-{node_counter}"
        nodes[node_id] = {
            "cpu": cpu, "used_cpu": 0, "pods": [],
            "status": "healthy", "container_id": container.id,
            "auto_scaled": False
        }
        heartbeats[node_id] = time.time()
        node_counter += 1
        print(f"Added node {node_id} with {cpu} CPU")
    except Exception as e:
        print(f"Error adding node: {e}")
    
    return redirect('/dashboard')

@app.route('/delete_node', methods=['POST'])
def delete_node():
    node_id = request.form['node_id']
    
    if node_id in nodes:
        # Check if node has pods
        if len(nodes[node_id]["pods"]) > 0:
            # Can't delete node with pods
            return redirect('/dashboard')
        
        # Remove the container
        try:
            container = client.containers.get(nodes[node_id]["container_id"])
            container.stop()
            container.remove()
        except Exception as e:
            print(f"Error removing container: {e}")
        
        # Remove node from data structures
        del nodes[node_id]
        del heartbeats[node_id]
        print(f"Deleted node {node_id}")
    
    return redirect('/dashboard')

@app.route('/launch_pod', methods=['POST'])
def launch_pod():
    global pod_counter
    cpu = int(request.form['cpu'])
    node_id = request.form.get('node_id')
    
    if node_id:
        # Manual assignment to specific node
        if node_id in nodes and nodes[node_id]["status"] == "healthy":
            avail = nodes[node_id]["cpu"] - nodes[node_id]["used_cpu"]
            if avail >= cpu:
                pod_id = f"pod-{pod_counter}"
                pods[pod_id] = {"cpu": cpu, "node_id": node_id, "status": "running"}
                nodes[node_id]["used_cpu"] += cpu
                nodes[node_id]["pods"].append(pod_id)
                pod_counter += 1
                print(f"Launched pod {pod_id} on specified node {node_id}")
            else:
                print(f"Not enough resources on node {node_id}")
    else:
        # Use scheduler to assign
        pod_id, assigned_node_id = schedule_pod(cpu)
        if pod_id:
            pods[pod_id] = {"cpu": cpu, "node_id": assigned_node_id, "status": "running"}
            nodes[assigned_node_id]["used_cpu"] += cpu
            nodes[assigned_node_id]["pods"].append(pod_id)
            pod_counter += 1
            print(f"Launched pod {pod_id} on {assigned_node_id} using {SCHEDULING_ALGORITHM} algorithm")
        else:
            print(f"Failed to launch pod - no suitable node found")
    
    return redirect('/dashboard')

def schedule_pod(cpu_req):
    global pod_counter
    
    print(f"Scheduling pod with {cpu_req} CPU using {SCHEDULING_ALGORITHM} algorithm")
    
    if SCHEDULING_ALGORITHM == "first-fit":
        return first_fit_scheduler(cpu_req)
    elif SCHEDULING_ALGORITHM == "best-fit":
        return best_fit_scheduler(cpu_req)
    elif SCHEDULING_ALGORITHM == "worst-fit":
        return worst_fit_scheduler(cpu_req)
    else:
        return best_fit_scheduler(cpu_req)  # Default to best-fit

def first_fit_scheduler(cpu_req):
    """First-Fit scheduling algorithm - allocates to first node with sufficient resources"""
    global pod_counter
    for node_id, info in nodes.items():
        if info["status"] != "healthy":
            continue
        avail = info["cpu"] - info["used_cpu"]
        if avail >= cpu_req:
            pod_id = f"pod-{pod_counter}"
            return pod_id, node_id
    return None, None

def best_fit_scheduler(cpu_req):
    """Best-Fit scheduling algorithm - allocates to node with minimum remaining resources"""
    global pod_counter
    best_node = None
    min_remain = float("inf")
    for node_id, info in nodes.items():
        if info["status"] != "healthy":
            continue
        avail = info["cpu"] - info["used_cpu"]
        if avail >= cpu_req and avail < min_remain:
            best_node = node_id
            min_remain = avail
    if best_node:
        pod_id = f"pod-{pod_counter}"
        return pod_id, best_node
    return None, None

def worst_fit_scheduler(cpu_req):
    """Worst-Fit scheduling algorithm - allocates to node with maximum remaining resources"""
    global pod_counter
    worst_node = None
    max_remain = -1
    for node_id, info in nodes.items():
        if info["status"] != "healthy":
            continue
        avail = info["cpu"] - info["used_cpu"]
        if avail >= cpu_req and avail > max_remain:
            worst_node = node_id
            max_remain = avail
    if worst_node:
        pod_id = f"pod-{pod_counter}"
        return pod_id, worst_node
    return None, None

@app.route('/heartbeat/<node_id>', methods=['POST'])
def heartbeat(node_id):
    if node_id in nodes:
        heartbeats[node_id] = time.time()
        nodes[node_id]["status"] = "healthy"
        return jsonify({"status": "Heartbeat OK"})
    return jsonify({"error": "Node not found"}), 404

@app.route('/set_scheduling_algorithm', methods=['POST'])
def set_scheduling_algorithm():
    """API endpoint to change the scheduling algorithm"""
    global SCHEDULING_ALGORITHM
    algorithm = request.form.get('algorithm')
    if algorithm in ["first-fit", "best-fit", "worst-fit"]:
        SCHEDULING_ALGORITHM = algorithm
        print(f"Changed scheduling algorithm to {algorithm}")
    return redirect('/dashboard')

@app.route('/toggle_auto_scaling', methods=['POST'])
def toggle_auto_scaling():
    """API endpoint to toggle auto-scaling"""
    global AUTO_SCALING_ENABLED
    AUTO_SCALING_ENABLED = not AUTO_SCALING_ENABLED
    print(f"Auto-scaling {'enabled' if AUTO_SCALING_ENABLED else 'disabled'}")
    return redirect('/dashboard')

@app.route('/simulate_node_failure', methods=['POST'])
def simulate_node_failure():
    """Simulate a node failure for testing recovery mechanisms"""
    node_id = request.form.get('node_id')
    if node_id in nodes:
        print(f"Simulating failure for node {node_id}")
        nodes[node_id]["status"] = "unresponsive"
        # Force immediate failure detection
        heartbeats[node_id] = time.time() - NODE_TIMEOUT - 1
    return redirect('/dashboard')

@app.route('/add_network_policy', methods=['POST'])
def add_network_policy():
    """Add a network policy between pods"""
    source_pod = request.form.get('source_pod')
    target_pod = request.form.get('target_pod')
    policy_type = request.form.get('policy_type', 'allow')  # 'allow' or 'deny'
    
    if source_pod and target_pod and source_pod in pods and target_pod in pods:
        policy_id = f"policy-{len(network_policies) + 1}"
        network_policies[policy_id] = {
            "source_pod": source_pod,
            "target_pod": target_pod,
            "policy_type": policy_type
        }
        print(f"Added network policy {policy_id}: {policy_type} from {source_pod} to {target_pod}")
    
    return redirect('/dashboard')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
