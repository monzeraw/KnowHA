# KnowHA - AI-Powered Knowledge Document Assistant

🚀 An intelligent web application that helps you create, analyze, and enhance technical knowledge documents using AI.

## ✨ Features

- **Document Type Selection**: Support for Best Practices, Lessons Learned, Engineering Reports, and Engineering Standards
- **Dual Input Methods**: 
  - Upload existing documents (PDF/DOCX)
  - Create new content with rich text editor (Quill.js)
- **AI-Powered Analysis**: Intelligent document analysis using ChatGPT (GPT-4o-mini)
- **Smart Suggestions**: Get improvement recommendations and quality scores
- **Modern UI**: Beautiful, responsive interface with animations and gradients
- **Progress Tracking**: Visual step-by-step workflow

## 🛠️ Technologies

- **Backend**: Flask (Python)
- **AI**: OpenAI GPT-4o-mini
- **Frontend**: HTML5, Tailwind CSS, JavaScript
- **Rich Text Editor**: Quill.js
- **Icons**: Font Awesome
- **Document Processing**: PyPDF2, python-docx

## 📋 Prerequisites

- Python 3.8+
- OpenAI API Key

## 🚀 Installation

1. Clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/knowha.git
cd knowha
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory:
```env
OPENAI_API_KEY=your-openai-api-key-here
FLASK_SECRET_KEY=your-secret-key-here
```

4. Run the application:
```bash
python3 app.py
```

5. Open your browser and navigate to:
```
http://127.0.0.1:5002
```

## 📁 Project Structure

```
KnowHA/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in repo)
├── static/
│   ├── app.js            # Frontend JavaScript
│   └── styles.css        # Custom styles
├── templates/
│   ├── layout.html       # Base template with modern UI
│   ├── index.html        # Landing page
│   └── steps/
│       ├── step1.html    # Document type selection
│       ├── step2.html    # Upload/Create document
│       ├── step3.html    # AI analysis
│       ├── step4.html    # Enhancement
│       └── step5.html    # Review & export
├── templates/            # Document templates
├── samples/              # Sample documents
└── uploads/              # User uploads (gitignored)
```

## 🎯 Usage

1. **Select Document Type**: Choose from Best Practices, Lessons Learned, Engineering Report, or Engineering Standards
2. **Upload or Create**: Either upload an existing document or create new content using the rich text editor
3. **AI Analysis**: Get instant AI-powered analysis with structure breakdown and improvement suggestions
4. **Enhance**: Apply AI recommendations to improve your document
5. **Review & Export**: Download your enhanced document

## 🔑 Environment Variables

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `FLASK_SECRET_KEY` | Secret key for Flask sessions |

## 📝 API Endpoints

- `GET /` - Landing page
- `GET /step/<int:step_number>` - Step pages
- `POST /api/select-type` - Select document type
- `POST /api/upload` - Upload document
- `POST /api/save-editor-content` - Save rich text content
- `POST /api/analyze` - Analyze document with AI
- `POST /api/next-step` - Navigate to next step

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License.

## 👤 Author

Your Name

## 🙏 Acknowledgments

- OpenAI for GPT-4o-mini API
- Quill.js for the rich text editor
- Tailwind CSS for the styling framework
- Font Awesome for the icons

## 📧 Support

For support, email your-email@example.com or open an issue in the repository.
