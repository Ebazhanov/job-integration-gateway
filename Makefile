## dev: Run backend only until frontend package.json is initialized
dev: dev-backend

dev-backend:
	python main.py

dev-frontend:
	cd frontend && npm run dev