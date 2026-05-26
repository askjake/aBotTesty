#!/bin/bash
# Frontend Setup Script
# Run this after cloning the repo

echo "🎨 Setting up Frontend Environment..."

# Check if we're in the right directory
if [ ! -f "pnpm-workspace.yaml" ]; then
    echo "❌ Error: Run this from the frontend directory"
    exit 1
fi

# Create .env.local files if they don't exist
echo ""
echo "📝 Creating .env.local files..."

for app in apps/chats apps/beta-reports; do
    if [ ! -f "$app/.env.local" ]; then
        if [ -f "$app/.env.example" ]; then
            cp "$app/.env.example" "$app/.env.local"
            echo "✅ Created: $app/.env.local"
        else
            echo "⚠️  No .env.example found for $app"
        fi
    else
        echo "✓  $app/.env.local already exists"
    fi
done

echo ""
echo "📦 Installing dependencies..."
pnpm install

echo ""
echo "✅ Frontend setup complete!"
echo ""
echo "To start development server:"
echo "  pnpm dev"
echo ""
echo "The frontend will be available at:"
echo "  http://localhost:3000"
echo ""
