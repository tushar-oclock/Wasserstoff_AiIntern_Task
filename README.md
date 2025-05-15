# Document Research & Theme Identification Chatbot

This project is an interactive chatbot that performs research across large document sets, identifies common themes, and provides detailed, cited responses to user queries.

## Features

- **Document Upload**: Support for PDF, Images (with OCR), and text files
- **Theme Identification**: Automatically identifies common themes across multiple documents
- **Cited Responses**: Provides detailed responses with citations to specific document locations
- **Document Management**: Interface to view and select specific documents for targeted queries
- **Theme Visualization**: Visual representation of identified themes and their relationships

## Technology Stack

- **Backend**: Flask, Python 3.11
- **LLM**: Groq API with Llama3 models
- **Vector Database**: ChromaDB for efficient semantic search
- **OCR**: Support for extracting text from images and scanned documents
- **UI**: Bootstrap with responsive design

## Project Structure

```
chatbot_theme_identifier/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── services/
│   │   ├── main.py
│   │   └── config.py
│   ├── data/
│   ├── Dockerfile
│   └── requirements.txt
├── docs/
├── tests/
├── demo/
└── README.md
```

## Installation

1. Clone the repository:
   ```
   git clone [repository URL]
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `.env` file with your API keys:
   ```
   GROQ_API_KEY=your_groq_api_key
   ```

4. Run the application:
   ```
   python main.py
   ```

## Usage

1. Access the application at `http://localhost:5000`
2. Upload documents using the upload interface
3. Enter queries in natural language
4. Review document-specific responses and identified themes
5. Export results as needed

## Requirements

- Python 3.11+
- GROQ API key
- Sufficient storage for document processing

## License

[License information]

## Acknowledgements

- This project was developed as part of the Wasserstoff Gen-AI Internship Task.