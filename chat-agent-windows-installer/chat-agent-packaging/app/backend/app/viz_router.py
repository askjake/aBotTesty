"""
Thought Visualization Router
Serves the AI thought visualization UI and handles real-time events
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.responses import Response
import queue
import threading
import time
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/viz", tags=["visualization"])

# Global state for capturing live events
live_events = queue.Queue()
thought_graph = {"nodes": [], "links": []}
context_memory = {}
tool_timeline = []
metrics = {"tokens": 0, "tools": 0, "time": 0}
node_counter = 0

# HTML template for the visualization
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Thought Visualization - LIVE</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a0a2e 100%);
            color: #00ff00;
            overflow: hidden;
        }
        
        .header {
            background: rgba(255, 0, 255, 0.1);
            border-bottom: 2px solid #ff00ff;
            padding: 15px;
            text-align: center;
            box-shadow: 0 0 20px rgba(255, 0, 255, 0.5);
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 0, 255, 0.5); }
            50% { box-shadow: 0 0 40px rgba(255, 0, 255, 0.8); }
        }
        
        h1 {
            color: #ff00ff;
            text-shadow: 0 0 10px #ff00ff;
            font-size: 2em;
            letter-spacing: 3px;
        }
        
        .status {
            color: #00ff00;
            font-size: 0.9em;
            margin-top: 5px;
        }
        
        .container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            grid-template-rows: 1fr 1fr;
            gap: 10px;
            padding: 10px;
            height: calc(100vh - 100px);
        }
        
        .panel {
            background: rgba(0, 0, 0, 0.7);
            border: 1px solid #00ff00;
            border-radius: 5px;
            padding: 15px;
            overflow: auto;
            box-shadow: 0 0 15px rgba(0, 255, 0, 0.3);
        }
        
        .panel h2 {
            color: #00ffff;
            border-bottom: 1px solid #00ffff;
            padding-bottom: 5px;
            margin-bottom: 10px;
            font-size: 1.2em;
        }
        
        #graph { grid-row: 1 / 3; }
        
        #graph svg {
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            border-radius: 5px;
        }
        
        .node circle {
            stroke: #fff;
            stroke-width: 2px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .node:hover circle {
            r: 12;
            filter: drop-shadow(0 0 10px currentColor);
        }
        
        .node text {
            font-size: 10px;
            fill: #fff;
            text-anchor: middle;
            pointer-events: none;
        }
        
        .link {
            stroke: #00ff00;
            stroke-opacity: 0.6;
            stroke-width: 2px;
            fill: none;
        }
        
        .event-item {
            padding: 5px;
            margin: 3px 0;
            background: rgba(0, 255, 0, 0.1);
            border-left: 3px solid #00ff00;
            font-size: 0.85em;
            animation: slideIn 0.3s;
        }
        
        @keyframes slideIn {
            from { transform: translateX(-20px); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        .event-item.tool { border-left-color: #ff0000; background: rgba(255, 0, 0, 0.1); }
        .event-item.decision { border-left-color: #ffff00; background: rgba(255, 255, 0, 0.1); }
        
        .timestamp {
            color: #666;
            font-size: 0.8em;
        }
        
        .context-item {
            padding: 5px;
            margin: 5px 0;
            background: rgba(0, 255, 255, 0.1);
            border-radius: 3px;
        }
        
        .context-key {
            color: #00ffff;
            font-weight: bold;
        }
        
        .metric {
            display: inline-block;
            margin: 10px;
            padding: 10px 20px;
            background: rgba(255, 0, 255, 0.2);
            border: 1px solid #ff00ff;
            border-radius: 5px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 2em;
            color: #ff00ff;
            font-weight: bold;
        }
        
        .metric-label {
            font-size: 0.8em;
            color: #aaa;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 AI THOUGHT VISUALIZATION - LIVE MODE 🧠</h1>
        <div class="status">● ACTIVE - Capturing real-time reasoning</div>
    </div>
    
    <div class="container">
        <div class="panel" id="graph">
            <h2>Reasoning Graph (Live)</h2>
            <svg id="graph-svg"></svg>
        </div>
        
        <div class="panel">
            <h2>Context Memory</h2>
            <div id="context"></div>
            <h2 style="margin-top: 20px;">Metrics</h2>
            <div id="metrics">
                <div class="metric">
                    <div class="metric-value" id="metric-tokens">0</div>
                    <div class="metric-label">Tokens</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="metric-tools">0</div>
                    <div class="metric-label">Tools</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="metric-time">0s</div>
                    <div class="metric-label">Time</div>
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>Event Log</h2>
            <div id="events"></div>
        </div>
    </div>
    
    <script>
        // D3 graph setup
        const svg = d3.select("#graph-svg");
        const width = svg.node().parentElement.clientWidth;
        const height = svg.node().parentElement.clientHeight;
        
        svg.attr("width", width).attr("height", height);
        
        const simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(30));
        
        let linkGroup = svg.append("g").attr("class", "links");
        let nodeGroup = svg.append("g").attr("class", "nodes");
        
        const colorMap = {
            thinking: "#00ff00",
            tool: "#ff0000",
            decision: "#ffff00",
            result: "#00ffff"
        };
        
        // Poll for updates every 2 seconds
        async function pollUpdates() {
            try {
                const response = await fetch('/rest/api/v1/viz/state');
                const data = await response.json();
                
                // Update graph
                updateGraph(data.graph);
                
                // Update context
                updateContext(data.context);
                
                // Update metrics
                updateMetrics(data.metrics);
                
                // Update events
                updateEvents(data.events);
            } catch (err) {
                console.error('Failed to poll updates:', err);
            }
            
            setTimeout(pollUpdates, 2000);
        }
        
        function updateGraph(graph) {
            if (!graph || !graph.nodes) return;
            
            // Update links
            const links = linkGroup.selectAll("path")
                .data(graph.links, d => `${d.source.id || d.source}-${d.target.id || d.target}`);
            
            links.enter()
                .append("path")
                .attr("class", "link")
                .merge(links);
            
            links.exit().remove();
            
            // Update nodes
            const nodes = nodeGroup.selectAll("g")
                .data(graph.nodes, d => d.id);
            
            const nodeEnter = nodes.enter()
                .append("g")
                .attr("class", "node")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            nodeEnter.append("circle")
                .attr("r", 8)
                .attr("fill", d => colorMap[d.category] || "#00ff00");
            
            nodeEnter.append("text")
                .attr("dy", 20)
                .text(d => d.label);
            
            nodeEnter.append("title")
                .text(d => d.full_text);
            
            // Update simulation
            simulation.nodes(graph.nodes);
            simulation.force("link").links(graph.links);
            simulation.alpha(0.3).restart();
        }
        
        simulation.on("tick", () => {
            linkGroup.selectAll("path")
                .attr("d", d => {
                    const dx = d.target.x - d.source.x;
                    const dy = d.target.y - d.source.y;
                    return `M${d.source.x},${d.source.y} L${d.target.x},${d.target.y}`;
                });
            
            nodeGroup.selectAll("g")
                .attr("transform", d => `translate(${d.x},${d.y})`);
        });
        
        function dragstarted(event, d) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }
        
        function dragged(event, d) {
            d.fx = event.x;
            d.fy = event.y;
        }
        
        function dragended(event, d) {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }
        
        function updateContext(context) {
            if (!context) return;
            const contextDiv = document.getElementById('context');
            contextDiv.innerHTML = Object.entries(context).map(([key, value]) => `
                <div class="context-item">
                    <span class="context-key">${key}:</span> ${JSON.stringify(value)}
                </div>
            `).join('');
        }
        
        function updateMetrics(metrics) {
            if (!metrics) return;
            document.getElementById('metric-tokens').textContent = metrics.tokens || 0;
            document.getElementById('metric-tools').textContent = metrics.tools || 0;
            document.getElementById('metric-time').textContent = (metrics.time || 0).toFixed(1) + 's';
        }
        
        function updateEvents(events) {
            if (!events || events.length === 0) return;
            const eventsDiv = document.getElementById('events');
            events.slice(-10).forEach(event => {
                const item = document.createElement('div');
                item.className = `event-item ${event.type}`;
                item.innerHTML = `
                    <span class="timestamp">${new Date(event.timestamp).toLocaleTimeString()}</span>
                    <div>${event.message}</div>
                `;
                eventsDiv.insertBefore(item, eventsDiv.firstChild);
            });
            
            // Keep only last 50 events
            while (eventsDiv.children.length > 50) {
                eventsDiv.removeChild(eventsDiv.lastChild);
            }
        }
        
        // Start polling
        pollUpdates();
    </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def get_viz_ui():
    """Serve the visualization UI"""
    return HTMLResponse(content=HTML_TEMPLATE)


@router.get("/state")
async def get_viz_state():
    """Get current visualization state"""
    return JSONResponse({
        "graph": thought_graph,
        "context": context_memory,
        "metrics": metrics,
        "events": tool_timeline[-20:] if tool_timeline else []
    })


@router.post("/event")
async def receive_event(request: Request):
    """Receive events from the thought interceptor"""
    global node_counter
    
    try:
        event = await request.json()
        
        if event.get("type") == "thought":
            # Add node to graph
            node_counter += 1
            node = {
                "id": node_counter,
                "label": event["text"][:50] + "..." if len(event["text"]) > 50 else event["text"],
                "category": event.get("category", "thinking"),
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "full_text": event["text"]
            }
            thought_graph["nodes"].append(node)
            
            # Link to previous node
            if len(thought_graph["nodes"]) > 1:
                thought_graph["links"].append({
                    "source": node_counter - 1,
                    "target": node_counter
                })
            
            tool_timeline.append({
                "type": "thought",
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "message": event["text"]
            })
        
        elif event.get("type") == "tool":
            metrics["tools"] += 1
            tool_timeline.append({
                "type": "tool",
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "message": f"🔧 {event.get('tool', 'unknown')}"
            })
        
        elif event.get("type") == "decision":
            node_counter += 1
            node = {
                "id": node_counter,
                "label": "Decision: " + event["text"][:40],
                "category": "decision",
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "full_text": event["text"]
            }
            thought_graph["nodes"].append(node)
            
            if len(thought_graph["nodes"]) > 1:
                thought_graph["links"].append({
                    "source": node_counter - 1,
                    "target": node_counter
                })
            
            tool_timeline.append({
                "type": "decision",
                "timestamp": event.get("timestamp", datetime.now().isoformat()),
                "message": f"⚖️  {event['text']}"
            })
        
        elif event.get("type") == "context":
            context_memory[event["key"]] = event["value"]
        
        elif event.get("type") == "metric":
            metrics[event["metric"]] = event["value"]
        
        return JSONResponse({"status": "ok"})
    
    except Exception as e:
        logger.error(f"Error receiving event: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=400)


@router.post("/clear")
async def clear_viz_state():
    """Clear all visualization state"""
    global node_counter, thought_graph, context_memory, tool_timeline, metrics
    
    node_counter = 0
    thought_graph = {"nodes": [], "links": []}
    context_memory = {}
    tool_timeline = []
    metrics = {"tokens": 0, "tools": 0, "time": 0}
    
    return JSONResponse({"status": "cleared"})
