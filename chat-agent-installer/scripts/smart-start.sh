#!/bin/bash
set -e

echo "🚀 Smart Chat Agent Startup"
echo "======================================"
echo

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$REPO_ROOT/app/backend"
FRONTEND_DIR="$REPO_ROOT/app/frontend"

# Run environment detection
echo "Step 1: Environment Detection"
echo "------------------------------"
python3 "$SCRIPT_DIR/detect-environment.py" || exit 1

echo
echo "Step 2: Backend Setup"
echo "------------------------------"
cd "$BACKEND_DIR"

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "✓ Backend ready"

echo
echo "Step 3: Frontend Setup"
echo "------------------------------"
cd "$FRONTEND_DIR"

# Create workspace file if missing
if [ ! -f "pnpm-workspace.yaml" ]; then
    cat > pnpm-workspace.yaml << 'EOF'
packages:
  - 'apps/*'
  - 'shared/*'
EOF
    echo "✓ Created pnpm-workspace.yaml"
fi

# Install dependencies
if [ ! -d "node_modules" ]; then
    echo "Installing Node dependencies (this may take a while)..."
    pnpm install --no-frozen-lockfile
fi

echo "✓ Frontend ready"

echo
echo "Step 4: Starting Services"
echo "------------------------------"

# Start backend in background
cd "$BACKEND_DIR"
source venv/bin/activate
echo "Starting backend on http://localhost:8000..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

# Wait for backend
sleep 3

# Start frontend
cd "$FRONTEND_DIR"
echo "Starting frontend on http://localhost:3000..."
pnpm dev &
FRONTEND_PID=$!

# Wait for frontend
sleep 5

echo
echo "✅ Services Started!"
echo "======================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo
echo "Press Ctrl+C to stop all services"

# Wait and cleanup on exit
trap "echo '\nStopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

# Keep script running
wait
