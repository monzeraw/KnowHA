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

    analysisSection.innerHTML = `
        <div class="bg-white rounded-xl shadow-sm p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="space-y-4">
                    <h3 class="text-lg font-semibold text-gray-900">Document Structure</h3>
                    <ul class="space-y-2">
                        ${analysis.structure.map((item, index) => `
                            <li class="flex items-start space-x-2">
                                <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 text-sm">${index + 1}</span>
                                <span class="text-gray-700">${item}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
                <div class="space-y-4">
                    <h3 class="text-lg font-semibold text-gray-900">Improvement Suggestions</h3>
                    <ul class="space-y-2">
                        ${analysis.suggestions.map(suggestion => `
                            <li class="flex items-start space-x-2">
                                <svg class="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                </svg>
                                <span class="text-gray-700">${suggestion}</span>
                            </li>
                        `).join('')}
                    </ul>
                </div>
            </div>
            <div class="mt-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-2">Quality Score</h3>
                <div class="relative pt-1">
                    <div class="overflow-hidden h-2 text-xs flex rounded bg-blue-100">
                        <div class="rounded bg-blue-600 transition-all duration-500 ease-out" 
                             style="width: ${analysis.quality_score}%">
                        </div>
                    </div>
                    <div class="flex justify-between text-sm text-gray-600 mt-1">
                        <span>Score: ${analysis.quality_score}/100</span>
                        <span>${analysis.quality_score >= 80 ? '🌟 Excellent' : analysis.quality_score >= 60 ? '👍 Good' : '🔨 Needs Improvement'}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
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
