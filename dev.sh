#!/bin/bash

# Function to gracefully kill all background processes on exit (Ctrl+C)
cleanup() {
  echo ""
  echo "🛑 Stopping backend and frontend servers..."
  kill $(jobs -p) 2>/dev/null
  exit
}

trap cleanup EXIT INT TERM

echo "🚀 Starting Job Integration Gateway (Full-Stack)..."

# 1. Start Python Backend in the background
python main.py &

# 2. Start Frontend development server
cd frontend && npm run dev