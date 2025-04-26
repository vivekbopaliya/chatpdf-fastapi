# Chat-PDF

Chat-PDF is an intelligent document interface that allows users to upload PDFs and have interactive conversations with their content using natural language processing.

## Frontend Code
For the frontend React code, please refer [here](https://github.com/vivekbopaliya/chatpdf-reactjs).

## Installation (Backend)

### Prerequisites
- Python 3.8+: Install Python from its original [site](https://www.python.org/downloads/)
- PostgreSQL database

### Setup Instructions
1. Fork the repository into your own GitHub account
2. Clone your newly forked repository from GitHub onto your local computer
3. Run `python -m venv .venv` to create a virtual environment
4. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`

### Set Up Environment Variables
1. Create a `.env` file in the project root
2. Add your OpenAI API key (get one from [OpenAI](https://platform.openai.com/))
3. Add your database connection string
```
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql://username:password@localhost/chatpdf
```

### Run the Application
- Run the command `uvicorn main:app --reload` to start the application
- Navigate to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to test the APIs

## APIs

The application provides the following API endpoints:

### PDF Management
- **PDF Upload API**: Upload a PDF file and create a knowledge base
- **Get PDFs API**: Retrieve all uploaded PDFs
- **Get Single PDF API**: Get details of a specific PDF
- **Delete PDF API**: Remove a PDF and its associated conversations

### Conversation
- **Chat API**: Ask questions about PDF content
- **Get Conversations API**: Retrieve conversation history for a PDF

### Authentication
- **Register API**: Create a new user account
- **Login API**: Authenticate and receive a JWT token cookie
- **Logout API**: End the current session
- **Get Current User API**: Retrieve authenticated user details

## Basic Architecture on how Chat-PDF works

### File Handling

- API accepts a file and validates if it's a PDF. If not, it returns a 400 error.

### File Processing

- The PDF file is read, and its binary content is converted into bytes using IO.

### Database Interaction

- File metadata and conversations are stored in a PostgreSQL database for future retrieval.

### Text Extraction

- The content of pdf is extracted using FileReader from pypdf.

### Chunking Text

- The extracted text is divided into smaller chunks for efficient processing.

### Embedding Setup

- Embeddings are created from these chunks, establishing a chain to track the conversation.

### Semantic Search

- Semantic search is performed based on the user's question.

### Answer Retrieval

- Using OpenAI's language model, an appropriate answer is retrieved based on the semantic search results.


### Here are the links to the high-level and low-level design README files:
- [High-Level Design README](https://github.com/vivekbopaliya/chatpdf-fastapi/blob/main/docs/high_level_design/README.md)
- [Low-Level Design README](https://github.com/vivekbopaliya/chatpdf-fastapi/blob/main/docs/low_level_design/README.md)

