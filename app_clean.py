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
import google.generativeai as genai
from dotenv import load_dotenv

app = Flask(__name__)
app.secret_key = 'replace_with_a_secret_key'
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
        'sampleFile': 'samples/best_practices_sample.docx'
    },
    'lessonsLearned': {
        'title': 'Lessons Learned',
        'description': 'Capture insights from projects and experiences for future reference.',
        'templateFile': 'templates/lessons_learned_template.docx',
        'sampleFile': 'samples/lessons_learned_sample.docx'
    },
    'engineeringReport': {
        'title': 'Engineering Report',
        'description': 'Create formal technical reports with comprehensive analysis.',
        'templateFile': 'templates/engineering_report_template.docx',
        'sampleFile': 'samples/engineering_report_sample.docx'
    },
    'engineeringStandards': {
        'title': 'Engineering Standards',
        'description': 'Authoritative documents for technical criteria, methods, and practices in engineering.',
        'templateFile': 'templates/engineering_standards_template.docx',
        'sampleFile': 'samples/engineering_standards_sample.docx'
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

def analyze_with_gemini(content, doc_type, doc_info):
    """Analyze document content using Gemini API."""
    try:
        prompt = f"""
        Analyze this {doc_info['title']} and provide exactly:
        1. Five-point document structure (use numbers)
        2. Four specific improvement suggestions (use bullets)
        3. A quality score (0-100)
        
        Content excerpt:
        {content[:1000]}
        """

        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            prompt,
            generation_config={
                'max_output_tokens': 500,
                'temperature': 0.4,
                'top_p': 0.8,
            }
        )
        return response.text
    except Exception as e:
        print(f"Gemini analysis error: {str(e)}")
        return None

def parse_analysis_response(analysis):
    """Parse Gemini's response into structured data."""
    structure = ['Executive Summary', 'Introduction', 'Main Content', 'Analysis', 'Conclusion']
    suggestions = ['Add more detail', 'Include examples', 'Enhance formatting', 'Add references']
    quality_score = 75

    if not analysis:
        return structure, suggestions, quality_score

    lines = analysis.split('\n')
    struct_points = []
    suggest_points = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Structure points (numbered)
        if line and line[0].isdigit() and '.' in line:
            point = line.split('.', 1)[1].strip()
            if len(struct_points) < 5:
                struct_points.append(point)
        
        # Suggestions (bulleted)
        elif line and line[0] in '•-*':
            suggestion = line.strip('•-* ')
            if len(suggest_points) < 4:
                suggest_points.append(suggestion)
        
        # Quality score
        elif 'score' in line.lower():
            score_match = re.search(r'\d+', line)
            if score_match:
                score = int(score_match.group())
                if 0 <= score <= 100:
                    quality_score = score

    if len(struct_points) >= 3:
        structure = struct_points
    if len(suggest_points) >= 2:
        suggestions = suggest_points

    return structure, suggestions, quality_score

@app.route('/')
def index():
    # Reset session when returning to home
    session.clear()
    return render_template('index.html', knowledge_types=KNOWLEDGE_TYPES, step=1)

@app.route('/step/<int:step_number>', methods=['GET'])
def step(step_number):
    if step_number < 1 or step_number > 5:
        return redirect(url_for('index'))

    # Ensure proper flow
    if step_number > 1 and 'doc_type' not in session:
        flash('Please select a document type first')
        return redirect(url_for('step', step_number=1))
    if step_number > 2 and 'file_path' not in session:
        flash('Please upload a file first')
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
        
        # Store file info in session
        session['file_path'] = file_path
        session['file_info'] = {
            'name': filename,
            'size': os.path.getsize(file_path),
            'type': filename.rsplit('.', 1)[1].lower(),
            'uploaded_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'file_info': session['file_info'],
            'next_step': 3
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/analyze', methods=['POST'])
def analyze_document():
    """Analyze the uploaded document using Gemini API."""
    if 'file_path' not in session:
        return jsonify({'success': False, 'error': 'No file uploaded'})

    try:
        # Configure Gemini
        load_dotenv()
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not configured'})
            
        genai.configure(api_key=api_key)
        
        # Get document info
        file_path = session['file_path']
        doc_type = session['doc_type']
        doc_info = KNOWLEDGE_TYPES[doc_type]
        
        def run_analysis():
            """Run the document analysis."""
            try:
                # Extract text content
                content = ''
                if file_path.endswith('.pdf'):
                    content = extract_text_from_pdf(file_path)
                else:
                    content = extract_text_from_docx(file_path)

                return analyze_with_gemini(content, doc_type, doc_info)
            except Exception as e:
                print(f"Analysis error: {str(e)}")
                return None
        
        # Run analysis with timeout
        print("Starting analysis with timeout...")
        result_queue = queue.Queue()
        analysis_thread = threading.Thread(target=lambda: result_queue.put(run_analysis()))
        analysis_thread.start()
        analysis_thread.join(timeout=20)  # 20 second timeout
        
        if analysis_thread.is_alive():
            print("Analysis timed out")
            structure, suggestions, quality_score = parse_analysis_response(None)
        else:
            analysis = result_queue.get()
            structure, suggestions, quality_score = parse_analysis_response(analysis)
        
        # Prepare the final result
        analysis_result = {
            'structure': structure,
            'suggestions': suggestions,
            'quality_score': quality_score,
            'analyzed_at': datetime.now().isoformat()
        }
        
        # Store in session and return
        session['analysis'] = analysis_result
        return jsonify({
            'success': True,
            'next_step': 4,
            'analysis': analysis_result
        })
        
    except Exception as e:
        print(f"Analysis failed: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Analysis failed. Please try again.'
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
