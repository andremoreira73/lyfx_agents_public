# lyfX.ai AgentVerse

A Django- and LangGraph-based AI agent platform that provides specialized AI assistants for business automation and workflow optimization. The platform features multiple AI agents, each designed for specific tasks, with a modern web interface and API access.

## 🚀 Features

- **Multiple Specialized AI Agents**:
  - **CO2 Calculator (cccalc)**: Calculates carbon emissions and carbon credits for chemicals; for more information see our [blog](https://lyfx.ai/use-case-for-the-real-world-estimating-chemical-carbon-footprints-using-ai/).
  - **Lyras**: Company information assistant for lyfX.ai
  - **IM Scanner**: Scans German energy companies for interim management positions
- **Modern Chat Interfaces**:
  - Legacy chat interface with OpenAI Assistants API
  - Enhanced chat interface with markdown support
  - LangGraph-powered modern agent chat with state management
- **Advanced Architecture**:
  - LangGraph workflow orchestration
  - PostgreSQL-based conversation checkpointing
  - Async task processing with Celery
  - RESTful API for programmatic access
- **Enterprise Features**:
  - User authentication and authorization
  - Agent access control (public/private agents)
  - Admin interface for agent management
  - Docker support for easy deployment

## 🛠️ Tech Stack

- **Backend**: Django 5.2.1, Python 3.11
- **AI/LLM**: LangChain, LangGraph, OpenAI API
- **Database**: PostgreSQL (SQLite for development)
- **Cache/Queue**: Redis, Celery
- **Frontend**: Tailwind CSS, HTMX
- **Deployment**: Docker, Uvicorn

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL
- Redis
- Node.js (for Tailwind CSS)
- Docker & Docker Compose (optional)

## 🔧 Installation

### Using Docker (Recommended)

1. Clone the repository and create `.env` file:

```bash
   cp example.env .env  # Edit .env and add your API keys
```

2. Start the development environment:

```bash
docker-compose up -d
```

3. Run migrations:

```bash
docker-compose exec web python manage.py migrate
```

4. Create a superuser:

```bash
docker-compose exec web python manage.py createsuperuser
```

5. Access the application at `http://localhost:8000`

### Manual Installation

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
export OPENAI_API_KEY="your-key"
export LANGCHAIN_API_KEY="your-key"
export DATABASE_URL="postgresql://user:password@localhost/dbname"
# Add other required keys
```

4. Install and build Tailwind CSS:

```bash
cd theme/static_src
npm install
npm run build
cd ../..
```

5. Run migrations:

```bash
python manage.py migrate
python manage.py setup_checkpointer  # Initialize LangGraph tables
```

6. Create a superuser:

```bash
python manage.py createsuperuser
```

7. Run the development server:

```bash
python manage.py runserver
```

## 🏗️ Project Structure

```
lyfx_agents/
├── agents/              # Main agent management app
├── agent_chat/          # Modern LangGraph chat interface
├── chatapp/             # Legacy chat interface
├── chatapp_plus/        # Enhanced chat with markdown
├── langgraph_agents/    # LangGraph agent implementations
│   ├── cccalc/         # CO2 calculator agent
│   └── lyras/          # Company info agent
├── langgraph_api_1/     # API endpoints
├── IM_scanner/          # Job scanner agent
├── theme/               # Tailwind CSS theme
└── lyfx_agents/         # Django project settings
```

## 💻 Usage

### Web Interface

1. Navigate to `http://localhost:8000`
2. Log in with your credentials
3. Access the agent dashboard
4. Select an agent to start a conversation

### API Access

Create a thread and send messages:

```bash
# Create a thread
curl -X POST http://localhost:8000/api/threads \
  -H "Content-Type: application/json" \
  -d '{"metadata": {}}'

# Send a message
curl -X POST http://localhost:8000/api/threads/{thread_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "Hello"}'

# Create a run
curl -X POST http://localhost:8000/api/threads/{thread_id}/runs \
  -H "Content-Type: application/json" \
  -d '{"assistant_id": "cccalc"}'
```

### IM Scanner

Run the job scanner manually:

```bash
python manage.py run_IM_scanner
```

Or with cleanup of old data:

```bash
python manage.py run_IM_scanner --cleanup
```

## 🔐 Configuration

### Agent Access Control

Agents can be configured as:

- **Public**: Accessible to all authenticated users
- **Private**: Requires specific user permissions
- **Featured**: Highlighted on the home page

Manage agents in the Django admin at `/admin/agents/agent/`

### Environment Variables

Required environment variables:

- `OPENAI_API_KEY`: OpenAI API key
- `LANGCHAIN_API_KEY`: LangSmith API key
- `DATABASE_URL`: PostgreSQL connection string
- `SCRAPINGBEE_API_KEY`: For web scraping (IM Scanner)
- `LYFX_EMAIL_KEY`: Email service credentials

## 🚀 Production Deployment

1. Use the production Docker Compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. Configure nginx as a reverse proxy
3. Set up SSL certificates
4. Configure environment variables for production
5. Set `DEBUG=False` in production settings

## License

- **Code**: Licensed under **Apache-2.0**. See `LICENSE`.
- **Sample data** (files under `data/` or otherwise marked): **CC BY 4.0**. See `data_license/LICENSE`.

If you contribute, you agree that your contributions are licensed under the same terms.

## Support

For issues and questions:

- Check the logs in `logs/` directory
- Review Django admin panel
- contact info@lyfx.ai

## Author

- Andre Moreira
- a.moreira@lyfx.ai
