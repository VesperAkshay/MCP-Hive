# MCP-Hive Project

## Overview
MCP-Hive is a comprehensive project that combines a modern frontend interface with a powerful Python backend system. This repository houses the main project structure along with the backend as a Git submodule for separate versioning and management.

## Project Structure
- **Frontend**: Main application interface (to be implemented)
- **Backend**: Python-based MCP service integrated as a Git submodule that provides AI model integration through Google's Generative AI

## Backend as a Git Submodule
The backend is maintained as a Git submodule, which provides several benefits:

- **Independent Version Control**: The backend has its own Git repository and history, allowing for separate branching, tagging, and versioning.
- **Code Isolation**: Changes to the backend don't require changes to the main repository and vice versa.
- **Cleaner Development Workflow**: Frontend and backend teams can work independently without interfering with each other's code.
- **Dependency Management**: The backend manages its own dependencies and environment separately from the main project.
- **Reusability**: The backend can be used by other projects by simply adding it as a submodule.

### Working with the Submodule
When cloning this repository, you need to explicitly initialize and update the submodule:
```
git submodule init
git submodule update
```

When making changes to the backend:
1. Navigate to the backend directory: `cd backend`
2. Make your changes
3. Commit and push changes from within the submodule
4. Update the main repository to point to the new commit

### Submodule Path and URL
The backend submodule is located at `./backend` and points to its own repository. You can view the submodule details with:
```
git submodule status
```

## Features
- Integration with Large Language Models (LLMs) using Model Control Protocol (MCP)
- Conversation persistence using SQLite
- Efficient function/tool calling capabilities
- Environment-based configuration

## Tech Stack
### Frontend (Planned)
- Framework to be selected

### Backend (Implemented)
- Python 3.12+
- Google Generative AI SDK
- MCP (Model Control Protocol)
- SQLite for storage
- LangChain components

## Getting Started

### Prerequisites
- Python 3.12 or higher
- Git
- pip or uv package manager

### Installation
1. Clone this repository:
   ```
   git clone https://github.com/yourusername/MCP-Hive.git
   ```

2. Initialize and update the backend submodule:
   ```
   git submodule init
   git submodule update
   ```

3. Set up the backend:
   ```
   cd backend
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Create a `.env` file in the backend directory based on `.env.example`
   - Add your Google API key: `GOOGLE_API_KEY=your_api_key_here`

### Running the Application
- **Backend Service**:
  ```
  cd backend
  python client.py
  ```
- **Test Server**:
  ```
  cd backend
  python test_server.py
  ```

## Development

### Updating the Backend Submodule
To update the backend submodule to the latest version:
```
git submodule update --remote backend
```

### Backend Development
For more details about the backend implementation, please refer to the [Backend README](backend/README.md).

## License
[Your chosen license] 