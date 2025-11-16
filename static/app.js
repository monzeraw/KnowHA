// Global state
let selectedDocType = null;

// Generic error handler
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
        setTimeout(() => {
            errorDiv.classList.add('hidden');
        }, 5000);
    } else {
        alert(message);
    }
}

function getCurrentStep() {
    const path = window.location.pathname;
    const match = path.match(/\/step\/(\d+)/);
    return match ? parseInt(match[1]) : 1;
}

function updateNextButtonState(enabled) {
    const nextButton = document.querySelector('button[onclick="nextStep()"]');
    if (nextButton) {
        nextButton.disabled = !enabled;
        if (enabled) {
            nextButton.classList.remove('opacity-50', 'cursor-not-allowed');
        } else {
            nextButton.classList.add('opacity-50', 'cursor-not-allowed');
        }
    }
}

async function nextStep() {
    const currentStep = getCurrentStep();
    
    // Disable the button to prevent double clicks
    updateNextButtonState(false);
    
    try {
        // Step-specific validations
        if (currentStep === 1 && !selectedDocType) {
            showError('Please select a document type first');
            updateNextButtonState(true);
            return;
        }
        
        // For step 2, check if file is uploaded
        if (currentStep === 2 && !document.querySelector('.upload-status')) {
            showError('Please upload a file first');
            updateNextButtonState(true);
            return;
        }
        
        // Call the API to move to next step
        const response = await fetch('/api/next-step', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ current_step: currentStep })
        });
        
        const data = await response.json();
        if (data.success && data.next_step) {
            window.location.href = `/step/${data.next_step}`;
        } else {
            showError(data.error || 'Failed to proceed to next step');
            updateNextButtonState(true);
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to proceed to next step. Please try again.');
        updateNextButtonState(true);
    }
}

// Document type selection initialization
function initializeDocTypeSelection() {
    console.log('Initializing document type selection...');
    const docTypeCards = document.querySelectorAll('.document-type-card');
    
    if (!docTypeCards.length) {
        console.log('No document type cards found');
        return;
    }
    
    console.log('Found', docTypeCards.length, 'document type cards');
    
    docTypeCards.forEach(card => {
        card.addEventListener('click', async function() {
            const type = this.dataset.type;
            console.log('Card clicked:', type);
            
            // Remove selection from all cards
            docTypeCards.forEach(c => {
                c.classList.remove('selected');
                const checkIcon = c.querySelector('.check-icon');
                if (checkIcon) checkIcon.classList.add('hidden');
                const cardContent = c.querySelector('.card-content');
                if (cardContent) {
                    cardContent.classList.remove('border-blue-500', 'bg-blue-50');
                }
            });
            
            // Add selection to clicked card
            this.classList.add('selected');
            const checkIcon = this.querySelector('.check-icon');
            if (checkIcon) checkIcon.classList.remove('hidden');
            const cardContent = this.querySelector('.card-content');
            if (cardContent) {
                cardContent.classList.add('border-blue-500', 'bg-blue-50');
            }
            
            try {
                const response = await fetch('/api/select-type', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams({ type: type })
                });
                
                const data = await response.json();
                if (data.success) {
                    console.log('Selection successful:', type);
                    selectedDocType = type;
                    updateNextButtonState(true);
                } else {
                    console.error('Selection failed:', data.error);
                    showError(data.error || 'Failed to select document type');
                }
            } catch (error) {
                console.error('Error:', error);
                showError('Failed to select document type. Please try again.');
            }
        });
    });
    
    // Disable next button initially if no type is selected
    if (!selectedDocType) {
        updateNextButtonState(false);
    }
}

// File upload handling
function initializeFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    if (!uploadZone || !fileInput) return;

    uploadZone.addEventListener('click', () => fileInput.click());
    
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('border-blue-500');
    });
    
    uploadZone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('border-blue-500');
    });
    
    uploadZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        uploadZone.classList.remove('border-blue-500');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            await handleFileUpload(files[0]);
        }
    });
    
    fileInput.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            await handleFileUpload(e.target.files[0]);
        }
    });
}

async function handleFileUpload(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        if (data.success) {
            // Show success feedback
            const fileInfo = document.createElement('div');
            fileInfo.className = 'mt-6 p-4 bg-blue-50 rounded-lg upload-status';
            fileInfo.innerHTML = `
                <h4 class="font-medium text-blue-900">Current File:</h4>
                <p class="text-sm text-blue-800">${data.file_info.name} (${(data.file_info.size / 1024 / 1024).toFixed(2)}MB)</p>
            `;
            
            // Replace or add file info section
            const existingFileInfo = document.querySelector('.upload-status');
            if (existingFileInfo) {
                existingFileInfo.replaceWith(fileInfo);
            } else {
                document.getElementById('uploadZone').insertAdjacentElement('afterend', fileInfo);
            }
            
            // Switch to editor tab and populate with extracted text
            if (data.extracted_text && window.quillEditor) {
                // Switch to editor tab
                document.getElementById('tab-editor').click();
                
                // Populate editor with extracted text
                window.quillEditor.setText(data.extracted_text);
                
                // Show notification
                const notification = document.createElement('div');
                notification.className = 'mt-4 p-4 bg-green-50 border-2 border-green-200 rounded-xl';
                notification.innerHTML = `
                    <div class="flex items-center space-x-3">
                        <i class="fas fa-check-circle text-green-600 text-xl"></i>
                        <div>
                            <h4 class="text-lg font-semibold text-green-900">Text Extracted!</h4>
                            <p class="text-green-700 text-sm">Document text has been loaded into the editor. You can now edit it before analyzing.</p>
                        </div>
                    </div>
                `;
                
                const editorContainer = document.getElementById('content-editor');
                const existingNotification = editorContainer.querySelector('.bg-green-50');
                if (existingNotification) {
                    existingNotification.replaceWith(notification);
                } else {
                    editorContainer.insertBefore(notification, editorContainer.firstChild);
                }
                
                // Auto-save after a moment
                setTimeout(() => {
                    if (window.saveEditorContent) {
                        window.saveEditorContent();
                    }
                }, 1000);
            }
            
            // Update next button state
            updateNextButtonState(true);
        } else {
            showError(data.error || 'Failed to upload file');
        }
    } catch (error) {
        console.error('Error:', error);
        showError('Failed to upload file. Please try again.');
    }
}

// Analysis functionality
async function initializeAnalysis() {
    // Show loading state immediately
    const analysisSection = document.querySelector('.analysis-section');
    if (analysisSection) {
        analysisSection.innerHTML = `
            <div class="flex items-center justify-center p-8">
                <div class="text-center">
                    <svg class="animate-spin h-8 w-8 text-blue-600 mx-auto mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <p class="text-gray-600">Analyzing your document with ChatGPT...</p>
                    <p class="text-gray-500 text-sm mt-2">This may take 5-10 seconds</p>
                </div>
            </div>
        `;
    }

    try {
        console.log('Starting analysis...');
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        console.log('Response received:', response.status);
        const data = await response.json();
        console.log('Data:', data);
        
        if (data.success) {
            console.log('Analysis successful, displaying results');
            displayAnalysisResults(data.analysis);
            updateNextButtonState(true);
        } else {
            console.error('Analysis failed:', data.error);
            if (analysisSection) {
                analysisSection.innerHTML = `
                    <div class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                        <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                        <h3 class="text-lg font-semibold text-red-900 mb-2">Analysis Failed</h3>
                        <p class="text-red-700 mb-4">${data.error || 'Failed to analyze document'}</p>
                        <button onclick="window.location.reload()" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                            Try Again
                        </button>
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error during analysis:', error);
        if (analysisSection) {
            analysisSection.innerHTML = `
                <div class="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
                    <svg class="w-12 h-12 text-red-500 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <h3 class="text-lg font-semibold text-red-900 mb-2">Connection Error</h3>
                    <p class="text-red-700 mb-4">Failed to connect to the server. Please try again.</p>
                    <button onclick="window.location.reload()" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700">
                        Try Again
                    </button>
                </div>
            `;
        }
    }
}

// Display analysis results with a nice UI
function displayAnalysisResults(analysis) {
    const analysisSection = document.querySelector('.analysis-section');
    if (!analysisSection) return;

    // Build the analysis report HTML
    let html = `
        <div class="analysis-results slide-in">
            <!-- Color Legend -->
            <div class="mb-8 p-6 bg-gradient-to-r from-gray-50 to-gray-100 rounded-xl border border-gray-200">
                <h3 class="text-lg font-bold text-gray-900 mb-4 flex items-center space-x-2">
                    <i class="fas fa-info-circle text-blue-600"></i>
                    <span>Status Legend</span>
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="flex items-center space-x-3 p-3 bg-white rounded-lg shadow-sm">
                        <div class="w-4 h-4 rounded-full bg-green-500"></div>
                        <div>
                            <p class="font-semibold text-green-900">Exists</p>
                            <p class="text-xs text-green-700">Section is complete and well-documented</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3 p-3 bg-white rounded-lg shadow-sm">
                        <div class="w-4 h-4 rounded-full bg-yellow-500"></div>
                        <div>
                            <p class="font-semibold text-yellow-900">Partial</p>
                            <p class="text-xs text-yellow-700">Section exists but needs improvement</p>
                        </div>
                    </div>
                    <div class="flex items-center space-x-3 p-3 bg-white rounded-lg shadow-sm">
                        <div class="w-4 h-4 rounded-full bg-red-500"></div>
                        <div>
                            <p class="font-semibold text-red-900">Missing</p>
                            <p class="text-xs text-red-700">Section is completely absent</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Summary Stats -->
            <div class="mb-8 grid grid-cols-1 md:grid-cols-4 gap-4">
                <div class="bg-gradient-to-br from-green-50 to-green-100 p-6 rounded-xl border-2 border-green-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-green-700">Complete</p>
                            <p class="text-3xl font-bold text-green-900">${analysis.summary?.exists || 0}</p>
                        </div>
                        <i class="fas fa-check-circle text-green-500 text-3xl"></i>
                    </div>
                </div>
                <div class="bg-gradient-to-br from-yellow-50 to-yellow-100 p-6 rounded-xl border-2 border-yellow-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-yellow-700">Partial</p>
                            <p class="text-3xl font-bold text-yellow-900">${analysis.summary?.partial || 0}</p>
                        </div>
                        <i class="fas fa-exclamation-circle text-yellow-500 text-3xl"></i>
                    </div>
                </div>
                <div class="bg-gradient-to-br from-red-50 to-red-100 p-6 rounded-xl border-2 border-red-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-red-700">Missing</p>
                            <p class="text-3xl font-bold text-red-900">${analysis.summary?.missing || 0}</p>
                        </div>
                        <i class="fas fa-times-circle text-red-500 text-3xl"></i>
                    </div>
                </div>
                <div class="bg-gradient-to-br from-blue-50 to-blue-100 p-6 rounded-xl border-2 border-blue-200">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-sm font-medium text-blue-700">Score</p>
                            <p class="text-3xl font-bold text-blue-900">${analysis.quality_score || 0}%</p>
                        </div>
                        <i class="fas fa-chart-line text-blue-500 text-3xl"></i>
                    </div>
                </div>
            </div>

            <!-- Elements List -->
            <div class="mb-6">
                <h3 class="text-xl font-bold text-gray-900 mb-4 flex items-center space-x-2">
                    <i class="fas fa-list-check text-blue-600"></i>
                    <span>Document Elements Analysis</span>
                </h3>
                <div class="space-y-4">
    `;

    // Add each element
    if (analysis.elements && analysis.elements.length > 0) {
        analysis.elements.forEach((element, index) => {
            const statusClass = element.status.toLowerCase();
            const statusIcon = statusClass === 'exists' ? 'fa-check-circle' : 
                              statusClass === 'partial' ? 'fa-exclamation-circle' : 
                              'fa-times-circle';
            const statusColor = statusClass === 'exists' ? 'text-green-600' : 
                               statusClass === 'partial' ? 'text-yellow-600' : 
                               'text-red-600';

            html += `
                <div class="element-card ${statusClass} bg-white rounded-xl p-6 shadow-sm border border-gray-200" style="animation-delay: ${index * 0.1}s">
                    <div class="flex items-start justify-between mb-3">
                        <div class="flex items-center space-x-3">
                            <i class="fas ${statusIcon} ${statusColor} text-2xl"></i>
                            <h4 class="text-lg font-bold text-gray-900">${element.name}</h4>
                        </div>
                        <span class="status-badge status-${statusClass}">
                            ${element.status.toUpperCase()}
                        </span>
                    </div>
                    <p class="text-gray-700 mb-4">${element.description || ''}</p>
                    ${element.action ? `
                        <div class="mt-4 p-4 bg-blue-50 border-l-4 border-blue-500 rounded">
                            <p class="text-sm font-semibold text-blue-900 mb-1">
                                <i class="fas fa-lightbulb text-blue-600 mr-2"></i>Action Required:
                            </p>
                            <p class="text-sm text-blue-800">${element.action}</p>
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

    html += `
                </div>
            </div>

            <!-- Overall Recommendations -->
            ${analysis.recommendations && analysis.recommendations.length > 0 ? `
                <div class="mt-8 p-6 bg-gradient-to-r from-purple-50 to-pink-50 rounded-xl border-2 border-purple-200">
                    <h3 class="text-xl font-bold text-gray-900 mb-4 flex items-center space-x-2">
                        <i class="fas fa-magic text-purple-600"></i>
                        <span>Overall Recommendations</span>
                    </h3>
                    <ul class="space-y-3">
                        ${analysis.recommendations.map(rec => `
                            <li class="flex items-start space-x-3">
                                <i class="fas fa-arrow-right text-purple-600 mt-1"></i>
                                <span class="text-gray-700">${rec}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;

    analysisSection.innerHTML = html;
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const currentStep = getCurrentStep();
    console.log('Current step:', currentStep);
    
    // Initialize based on current step
    switch(currentStep) {
        case 1:
            initializeDocTypeSelection();
            break;
        case 2:
            initializeFileUpload();
            break;
        case 3:
            initializeAnalysis();
            break;
    }
});
