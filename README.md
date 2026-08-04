# legal_rag_agent

Enterprise Legal AI Platform featuring RAG-grounded statutory consultation, vector embeddings (Qdrant), document ingestion pipeline, and role-based access control.

## Tech Stack

### Backend
- **Framework:** FastAPI (Python)
- **Database Migrations:** Alembic
- **Vector Database:** Qdrant (for embeddings and similarity search)
- **Testing:** Pytest

### Frontend
- **Framework:** React 19 + Vite
- **Routing:** React Router
- **Icons:** Lucide React
- **Linting:** Oxlint

## Project Structure

- `/backend/` - Contains the FastAPI application, database schemas, services, and document ingestion pipeline scripts.
- `/frontend/` - Contains the Vite-React frontend web interface.

## Installation Guide

### Prerequisites
- Docker and Docker Compose (for PostgreSQL and Qdrant)
- Python 3.10+ 
- Node.js 18+

### 1. Database Setup
Start the PostgreSQL database and Qdrant vector store using Docker Compose:
```bash
cd backend
docker-compose up -d
```

### 2. Backend Setup
Activate the virtual environment and start the FastAPI server:
```bash
cd backend
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
# source venv/bin/activate

uvicorn app.main:app --reload
```

### 3. Frontend Setup
Install dependencies and run the Vite development server:
```bash
cd frontend
npm install
npm run dev
```

The application will be accessible at `http://localhost:5173` (Frontend) and the API docs at `http://localhost:8000/docs`.
