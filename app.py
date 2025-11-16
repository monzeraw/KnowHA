from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import os
import json
import re
import threading
import queue
from datetime import datetime
from docx import Document
import PyPDF2
import markdown
from openai import OpenAI
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Flask with secure secret key
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes
app.config['SESSION_TYPE'] = 'filesystem'

# Document types
KNOWLEDGE_TYPES = {
    'bestPractices': {
        'title': 'Best Practices',
        'description': 'Document proven methods and techniques that deliver superior results.',
        'templateFile': 'templates/best_practices_template.docx',
        'sampleFile': 'samples/best_practices_sample.docx',
        'elements': [
            'Executive Summary',
            'Introduction',
            'Scope and Context',
            'Best Practice Description',
            'Implementation Guidelines',
            'Benefits and Outcomes',
            'Supporting Evidence',
            'Recommendations',
            'Conclusion'
        ]
    },
    'lessonsLearned': {
        'title': 'Lessons Learned',
        'description': 'Capture insights from projects and experiences for future reference.',
        'templateFile': 'templates/lessons_learned_template.docx',
        'sampleFile': 'samples/lessons_learned_sample.docx',
        'elements': [
            'Executive Summary',
            'Project Background',
            'Problem Statement',
            'What Went Well',
            'What Went Wrong',
            'Root Cause Analysis',
            'Lessons Learned',
            'Recommendations',
            'Action Items'
        ]
    },
    'engineeringReport': {
        'title': 'Engineering Report',
        'description': 'Create formal technical reports with comprehensive analysis.',
        'templateFile': 'templates/engineering_report_template.docx',
        'sampleFile': 'samples/engineering_report_sample.docx',
        'elements': [
            'Title Page',
            'Abstract',
            'Table of Contents',
            'Introduction',
            'Methodology',
            'Results and Analysis',
            'Discussion',
            'Conclusions',
            'Recommendations',
            'References'
        ]
    },
    'engineeringStandards': {
        'title': 'Engineering Standards',
        'description': 'Authoritative documents for technical criteria, methods, and practices in engineering.',
        'templateFile': 'templates/engineering_standards_template.docx',
        'sampleFile': 'samples/engineering_standards_sample.docx',
        'elements': [
            'Title and Identification',
            'Scope',
            'Normative References',
            'Terms and Definitions',
            'Technical Requirements',
            'Test Methods',
            'Compliance Criteria',
            'Quality Assurance',
            'Documentation Requirements'
        ]
    }
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def extract_text_from_pdf(file_path):
    """Extract text from a PDF file."""
    text = ""
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extracting text from PDF: {str(e)}")
    return text

def extract_text_from_docx(file_path):
    """Extract text from a DOCX file."""
    text = ""
    try:
        doc = Document(file_path)
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
    except Exception as e:
        print(f"Error extracting text from DOCX: {str(e)}")
    return text

def analyze_with_chatgpt(content, doc_type, doc_info):
    """Analyze document content using ChatGPT API with element-based status."""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("No API key found")
            return None
            
        client = OpenAI(api_key=api_key)
        
        # Get expected elements for this document type
        expected_elements = doc_info.get('elements', [
            'Executive Summary',
            'Introduction',
            'Problem Statement',
            'Methodology',
            'Analysis',
            'Results',
            'Recommendations',
            'Conclusion'
        ])
        
        prompt = f"""
        Analyze this {doc_info['title']} document and evaluate the following required elements.
        For each element, determine its status: EXISTS (complete and well-documented), PARTIAL (present but needs improvement), or MISSING (completely absent).
        
        Required Elements to Check:
        {chr(10).join([f"- {elem}" for elem in expected_elements])}
        
        For each element, provide:
        1. Status (EXISTS, PARTIAL, or MISSING)
        2. Brief description of what you found (or what's missing)
        3. Specific action needed to improve (if PARTIAL or MISSING)
        
        Also provide:
        - Overall quality score (0-100)
        - 3-5 overall recommendations for the document
        
        Format your response as JSON:
        {{
            "elements": [
                {{
                    "name": "Element Name",
                    "status": "EXISTS|PARTIAL|MISSING",
                    "description": "What was found or what's missing",
                    "action": "What needs to be done (if applicable)"
                }}
            ],
            "quality_score": 75,
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        }}
        
        Document Content:
        {content[:4000]}
        """

        print("Sending request to OpenAI for element analysis...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a technical document analyst. Analyze documents by evaluating the presence and quality of required elements. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.3,
            timeout=30
        )
        
        result = response.choices[0].message.content
        print(f"Received response: {len(result)} characters")
        
        # Parse JSON response
        try:
            # Extract JSON from markdown code blocks if present
            if '```json' in result:
                result = result.split('```json')[1].split('```')[0].strip()
            elif '```' in result:
                result = result.split('```')[1].split('```')[0].strip()
            
            analysis_data = json.loads(result)
            
            # Calculate summary stats
            summary = {
                'exists': sum(1 for e in analysis_data['elements'] if e['status'].upper() == 'EXISTS'),
                'partial': sum(1 for e in analysis_data['elements'] if e['status'].upper() == 'PARTIAL'),
                'missing': sum(1 for e in analysis_data['elements'] if e['status'].upper() == 'MISSING')
            }
            analysis_data['summary'] = summary
            
            return analysis_data
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print(f"Response content: {result}")
            # Return default structure if JSON parsing fails
            return create_default_analysis(expected_elements)
            
    except Exception as e:
        print(f"ChatGPT analysis error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_default_analysis(expected_elements):
    """Create a default analysis structure when API fails."""
    return {
        "elements": [
            {
                "name": elem,
                "status": "PARTIAL",
                "description": "Unable to analyze - please try again",
                "action": "Re-run the analysis to get detailed feedback"
            }
            for elem in expected_elements[:5]
        ],
        "quality_score": 50,
        "recommendations": [
            "Ensure all required sections are present",
            "Add more detailed content to each section",
            "Include supporting evidence and examples"
        ],
        "summary": {
            "exists": 0,
            "partial": len(expected_elements[:5]),
            "missing": 0
        }
    }

def parse_analysis_response(analysis):
    """Legacy function - now analysis is returned as structured JSON."""
    # This function is kept for backward compatibility but is no longer used
    # Analysis is now returned directly as a dictionary from analyze_with_chatgpt
    if isinstance(analysis, dict):
        return analysis
    
    # Fallback for non-dict responses
    return {
        "elements": [],
        "quality_score": 0,
        "recommendations": [],
        "summary": {"exists": 0, "partial": 0, "missing": 0}
    }

@app.route('/')
def index():
    # Reset session when returning to home
    session.clear()
    return render_template('index.html', knowledge_types=KNOWLEDGE_TYPES, step=1)

@app.route('/step/<int:step_number>', methods=['GET'])
def step(step_number):
    if step_number < 1 or step_number > 6:
        return redirect(url_for('index'))

    # Ensure proper flow
    if step_number > 1 and 'doc_type' not in session:
        flash('Please select a document type first')
        return redirect(url_for('step', step_number=1))
    if step_number > 2 and 'file_path' not in session:
        flash('Please upload or create a document first')
        return redirect(url_for('step', step_number=2))
    if step_number > 3 and 'analysis' not in session:
        flash('Please complete the analysis first')
        return redirect(url_for('step', step_number=3))

    context = {
        'step': step_number,
        'knowledge_types': KNOWLEDGE_TYPES,
        'current_doc_type': session.get('doc_type'),
        'file_info': session.get('file_info'),
        'analysis': session.get('analysis'),
        'enhanced_content': session.get('enhanced_content')
    }
    
    return render_template(f'steps/step{step_number}.html', **context)

@app.route('/api/select-type', methods=['POST'])
def select_document_type():
    doc_type = request.form.get('type')
    if not doc_type or doc_type not in KNOWLEDGE_TYPES:
        return jsonify({'success': False, 'error': 'Invalid document type'})
        
    # Store document type in session
    session['doc_type'] = doc_type
    return jsonify({
        'success': True,
        'doc_type': doc_type,
        'type_info': KNOWLEDGE_TYPES[doc_type],
        'next_step': 2
    })

@app.route('/api/next-step', methods=['POST'])
def next_step():
    try:
        data = request.get_json()
        current_step = data.get('current_step', 1)
        
        # Validate current step
        if current_step < 1 or current_step > 5:
            return jsonify({'success': False, 'error': 'Invalid step'})
        
        # Check required session data for each step
        if current_step == 1:
            if 'doc_type' not in session:
                return jsonify({'success': False, 'error': 'Please select a document type first'})
        elif current_step == 2:
            if 'file_info' not in session:
                return jsonify({'success': False, 'error': 'Please upload a file first'})
        elif current_step == 3:
            if 'file_path' not in session:
                return jsonify({'success': False, 'error': 'Please upload a file first'})
            if 'analysis' not in session:
                return jsonify({'success': False, 'error': 'Analysis not completed'})
        elif current_step == 4:
            if 'enhanced_content' not in session:
                return jsonify({'success': False, 'error': 'Enhancement not completed'})
            
        next_step = min(current_step + 1, 5)
        return jsonify({
            'success': True,
            'next_step': next_step,
            'current_doc_type': session.get('doc_type'),
            'file_info': session.get('file_info')
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download_template/<doc_type>')
def download_template(doc_type):
    if doc_type not in KNOWLEDGE_TYPES:
        flash('Invalid document type')
        return redirect(url_for('index'))
    
    template_file = KNOWLEDGE_TYPES[doc_type]['templateFile']
    if not os.path.exists(template_file):
        flash('Template file not found')
        return redirect(url_for('index'))
    
    return send_file(template_file, as_attachment=True)

@app.route('/api/download_sample/<doc_type>')
def download_sample(doc_type):
    if doc_type not in KNOWLEDGE_TYPES:
        flash('Invalid document type')
        return redirect(url_for('index'))
    
    sample_file = KNOWLEDGE_TYPES[doc_type]['sampleFile']
    if not os.path.exists(sample_file):
        flash('Sample file not found')
        return redirect(url_for('index'))
    
    return send_file(sample_file, as_attachment=True)

@app.route('/api/upload', methods=['POST'])
def upload_document():
    if 'doc_type' not in session:
        return jsonify({'success': False, 'error': 'Please select a document type first'})

    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload a PDF or DOCX file'})

    try:
        # Create upload folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Extract text content
        extracted_text = ''
        if file_path.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        else:
            extracted_text = extract_text_from_docx(file_path)
        
        # Store file info in session
        session['file_path'] = file_path
        session['file_content'] = extracted_text
        session['file_info'] = {
            'name': filename,
            'size': os.path.getsize(file_path),
            'type': filename.rsplit('.', 1)[1].lower(),
            'uploaded_at': datetime.now().isoformat(),
            'source': 'upload'
        }
        
        return jsonify({
            'success': True,
            'file_info': session['file_info'],
            'extracted_text': extracted_text,
            'next_step': 3
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/save-editor-content', methods=['POST'])
def save_editor_content():
    """Save content from rich text editor."""
    if 'doc_type' not in session:
        return jsonify({'success': False, 'error': 'Please select a document type first'})

    try:
        data = request.get_json()
        content = data.get('content', '')
        text = data.get('text', '')
        
        if not text or len(text.strip()) < 50:
            return jsonify({'success': False, 'error': 'Content is too short. Please write at least 50 characters.'})
        
        # Create uploads folder if it doesn't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Save content as a temporary file
        filename = f"editor_content_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Store file info in session
        session['file_path'] = file_path
        session['file_content'] = text
        session['file_info'] = {
            'name': filename,
            'size': len(text.encode('utf-8')),
            'type': 'editor',
            'uploaded_at': datetime.now().isoformat(),
            'source': 'editor',
            'word_count': len(text.split())
        }
        
        return jsonify({
            'success': True,
            'file_info': session['file_info'],
            'next_step': 3
        })

    except Exception as e:
        print(f"Error saving editor content: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """Analyze the uploaded document using ChatGPT API."""
    if 'file_path' not in session:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    try:
        # Load environment variables (force reload)
        load_dotenv(override=True)
        api_key = os.getenv('OPENAI_API_KEY')
        print(f"API Key loaded: {'Yes' if api_key else 'No'}")
        print(f"API Key length: {len(api_key) if api_key else 0}")
        print(f"API Key starts with: {api_key[:10] if api_key else 'None'}...")
        
        if not api_key or api_key == 'your-openai-api-key-here':
            return jsonify({'success': False, 'error': 'OpenAI API key not configured. Please set OPENAI_API_KEY in .env file'})
        
        print("Starting ChatGPT analysis...")
        
        # Get document info
        file_path = session['file_path']
        doc_type = session['doc_type']
        doc_info = KNOWLEDGE_TYPES[doc_type]
        
        # Extract text content
        print("Extracting document content...")
        content = ''
        file_info = session.get('file_info', {})
        
        if file_info.get('source') == 'editor':
            # Content from rich text editor
            content = session.get('file_content', '')
            if not content:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
        elif file_path.endswith('.pdf'):
            content = extract_text_from_pdf(file_path)
        else:
            content = extract_text_from_docx(file_path)
        
        if not content or len(content.strip()) < 50:
            return jsonify({'success': False, 'error': 'Could not extract sufficient content from the document'})
        
        print(f"Extracted {len(content)} characters from document")
        
        # Analyze with ChatGPT
        print("Calling ChatGPT API...")
        analysis = analyze_with_chatgpt(content, doc_type, doc_info)
        
        if analysis is None:
            return jsonify({'success': False, 'error': 'ChatGPT analysis failed. Please check your API key and try again.'})
        
        print("Analysis completed successfully")
        
        # Analysis is now returned as a structured dictionary
        # Add timestamp
        analysis['analyzed_at'] = datetime.now().isoformat()
        
        # Store in session and return
        session['analysis'] = analysis
        return jsonify({
            'success': True,
            'next_step': 4,
            'analysis': analysis
        })
        
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Analysis failed: {str(e)}'
        })

@app.route('/api/enhance', methods=['POST'])
def enhance_document():
    if 'analysis' not in session:
        return jsonify({'success': False, 'error': 'Document not analyzed'})

    try:
        enhanced_content = {
            'original_text': session.get('file_content', ''),
            'improvements': [
                'Added executive summary',
                'Enhanced technical specifications',
                'Included reference standards',
                'Added data visualizations'
            ],
            'enhanced_at': datetime.now().isoformat()
        }

        session['enhanced_content'] = enhanced_content
        return jsonify({
            'success': True,
            'next_step': 5,
            'enhanced_content': enhanced_content
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/share', methods=['POST'])
def share_document():
    if 'enhanced_content' not in session:
        return jsonify({'success': False, 'error': 'Document not enhanced'})

    try:
        # Here you would implement sharing functionality
        share_info = {
            'shared_at': datetime.now().isoformat(),
            'share_url': 'https://example.com/share/123',
            'expiry': '24 hours'
        }

        return jsonify({
            'success': True,
            'share_info': share_info
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5002)
