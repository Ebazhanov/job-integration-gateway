dev:
	@$(MAKE) -j 2 dev-backend dev-frontend

dev-backend:
	uvicorn main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev