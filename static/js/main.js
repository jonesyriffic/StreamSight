/**
 * DocuSearch AI - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Initialize search overlay
    const searchInProgressOverlay = document.getElementById('searchInProgressOverlay');
    if (searchInProgressOverlay) {
        console.log('Search overlay initialized');
        // Make sure overlay is hidden initially
        searchInProgressOverlay.classList.remove('visible');
        searchInProgressOverlay.style.display = 'flex';
        searchInProgressOverlay.style.opacity = '0';
        searchInProgressOverlay.style.visibility = 'hidden';
        
        // Define the global showAISearchOverlay function
        window.showAISearchOverlay = function(query) {
            console.log('Showing AI search overlay for query:', query);
            // Update the query text
            const searchQueryElement = searchInProgressOverlay.querySelector('.search-query');
            if (searchQueryElement) {
                searchQueryElement.textContent = `"${query}"`;
            }
            
            // Show the overlay
            searchInProgressOverlay.classList.add('visible');
            searchInProgressOverlay.style.opacity = '1';
            searchInProgressOverlay.style.visibility = 'visible';
            
            // Start AI thinking process
            if (window.aiThinking) {
                window.aiThinking.start(query);
            }
        };
        
        // Initialize AI thinking process functions
        window.aiThinking = {
            /**
             * Start the AI thinking process with animated stages
             * @param {string} query - The search query
             */
            start: function(query) {
                // Clear any existing progress interval
                if (this.progressInterval) {
                    clearInterval(this.progressInterval);
                    this.progressInterval = null;
                }
                
                // Reset stages
                document.querySelectorAll('.thinking-stage').forEach(stage => {
                    stage.classList.remove('active', 'completed');
                });
                document.querySelector('.timeline-progress').style.width = '0%';
                
                // Start with first stage
                const firstStage = document.getElementById('stage-searching');
                firstStage.classList.add('active');
                
                // Update timeline progress
                document.querySelector('.timeline-progress').style.width = '10%';
                
                // Add detail to first stage
                firstStage.querySelector('.stage-detail').textContent = 'Scanning document library...';
                
                // Set up progression through stages
                this.simulateProgress();
            },
            
            /**
             * Get real-time search progress updates from the server
             */
            simulateProgress: function() {
                // Generate a query ID for this search session
                const queryId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
                
                // Start polling for progress updates
                this.progressInterval = setInterval(() => {
                    fetch(`/api/search/progress?query_id=${queryId}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                // Update the UI with the current stage information
                                this.updateStage(data.stage, data.detail, data.progress);
                                
                                // If we're at 100%, stop polling
                                if (data.progress >= 95) {
                                    clearInterval(this.progressInterval);
                                }
                            }
                        })
                        .catch(error => {
                            console.error('Error getting search progress:', error);
                            // Fall back to simulated progress on error
                            clearInterval(this.progressInterval);
                            this.fallbackSimulatedProgress();
                        });
                }, 1000); // Poll every second
            },
            
            /**
             * Fallback to simulated progress if API fails
             */
            fallbackSimulatedProgress: function() {
                const timings = [
                    { stage: 'searching', progress: 25, detail: 'Identifying relevant content...', time: 1500 },
                    { stage: 'analyzing', progress: 50, detail: 'Analyzing document relevance...', time: 3000 },
                    { stage: 'generating', progress: 75, detail: 'Synthesizing information...', time: 5000 },
                    { stage: 'finalizing', progress: 100, detail: 'Preparing response...', time: 7000 }
                ];
                
                timings.forEach((step, index) => {
                    setTimeout(() => {
                        const prevStage = index > 0 ? document.getElementById(`stage-${timings[index-1].stage}`) : null;
                        const currentStage = document.getElementById(`stage-${step.stage}`);
                        
                        // Update previous stage to completed
                        if (prevStage) {
                            prevStage.classList.remove('active');
                            prevStage.classList.add('completed');
                        }
                        
                        // Activate current stage
                        currentStage.classList.add('active');
                        
                        // Update timeline progress
                        document.querySelector('.timeline-progress').style.width = `${step.progress}%`;
                        
                        // Update stage detail
                        currentStage.querySelector('.stage-detail').textContent = step.detail;
                    }, step.time);
                });
            },
            
            /**
             * Update a specific stage with detailed information
             * @param {string} stage - The stage ID (searching, analyzing, generating, finalizing)
             * @param {string} detail - The detailed information to display
             * @param {number} progress - Progress percentage (0-100)
             */
            updateStage: function(stage, detail, progress) {
                const stageElement = document.getElementById(`stage-${stage}`);
                if (!stageElement) return;
                
                // Activate this stage, complete previous stages
                document.querySelectorAll('.thinking-stage').forEach(el => {
                    const stageId = el.id.replace('stage-', '');
                    const stageIndex = ['searching', 'analyzing', 'generating', 'finalizing'].indexOf(stageId);
                    const currentIndex = ['searching', 'analyzing', 'generating', 'finalizing'].indexOf(stage);
                    
                    if (stageIndex < currentIndex) {
                        el.classList.remove('active');
                        el.classList.add('completed');
                    } else if (stageIndex === currentIndex) {
                        el.classList.add('active');
                        el.classList.remove('completed');
                    } else {
                        el.classList.remove('active', 'completed');
                    }
                });
                
                // Update stage detail
                if (detail) {
                    stageElement.querySelector('.stage-detail').textContent = detail;
                }
                
                // Update timeline progress
                if (progress !== undefined) {
                    document.querySelector('.timeline-progress').style.width = `${progress}%`;
                }
            }
        };
    } else {
        console.error('Search overlay element not found in DOM!');
    }
    
    // Handle main search form submission to show the overlay
    const mainSearchForm = document.getElementById('searchForm');
    const searchResultsForm = document.getElementById('searchResultsForm');
    
    // Setup search form submission handler for homepage
    if (mainSearchForm) {
        mainSearchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('mainSearchInput');
            const query = searchInput?.value?.trim();
            
            if (query) {
                // Use the showAISearchOverlay function
                if (window.showAISearchOverlay) {
                    window.showAISearchOverlay(query);
                }
            }
        });
    }
    
    // Setup search form submission handler for search results page
    if (searchResultsForm) {
        searchResultsForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('searchResultsInput');
            const query = searchInput?.value?.trim();
            
            if (query) {
                // Use the showAISearchOverlay function
                if (window.showAISearchOverlay) {
                    window.showAISearchOverlay(query);
                }
            }
        });
    }
    
    // Voice search removed in favor of reliable text search

    // File input validation for single file input (like in reupload form)
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const fileError = document.getElementById('file-error');
            const fileWarning = document.getElementById('file-warning');
            
            // Remove any existing error or warning messages
            if (fileError) {
                fileError.remove();
            }
            if (fileWarning) {
                fileWarning.remove();
            }
            
            if (file) {
                // Check file type
                if (!file.type.match('application/pdf')) {
                    const errorMsg = document.createElement('div');
                    errorMsg.id = 'file-error';
                    errorMsg.classList.add('alert', 'alert-danger', 'mt-2');
                    errorMsg.textContent = 'Only PDF files are allowed';
                    fileInput.parentNode.appendChild(errorMsg);
                    fileInput.value = '';
                }
                
                // Check file size (max 100MB, but warn over 16MB)
                else if (file.size > 100 * 1024 * 1024) {
                    const errorMsg = document.createElement('div');
                    errorMsg.id = 'file-error';
                    errorMsg.classList.add('alert', 'alert-danger', 'mt-2');
                    errorMsg.textContent = 'File size must be less than 100MB';
                    fileInput.parentNode.appendChild(errorMsg);
                    fileInput.value = '';
                } 
                else if (file.size > 16 * 1024 * 1024) {
                    // Just warn the user that large files will use chunked upload
                    const warningMsg = document.createElement('div');
                    warningMsg.id = 'file-warning';
                    warningMsg.classList.add('alert', 'alert-warning', 'mt-2');
                    const fileSizeMB = Math.round(file.size / (1024 * 1024) * 10) / 10;
                    warningMsg.textContent = `Large file detected (${fileSizeMB} MB). Chunked upload will be used to handle this file reliably.`;
                    fileInput.parentNode.appendChild(warningMsg);
                }
            }
        });
    }
    
    // File input validation for multiple file input (upload page)
    const filesInput = document.getElementById('files');
    if (filesInput) {
        filesInput.addEventListener('change', function(e) {
            const files = e.target.files;
            const fileError = document.getElementById('files-error');
            const fileWarning = document.getElementById('files-warning');
            
            // Remove any existing error or warning messages
            if (fileError) {
                fileError.remove();
            }
            if (fileWarning) {
                fileWarning.remove();
            }
            
            if (files && files.length > 0) {
                let totalSize = 0;
                let invalidFiles = [];
                let largeFiles = [];
                
                // Check each file
                Array.from(files).forEach(file => {
                    totalSize += file.size;
                    
                    // Check file type
                    if (!file.type.match('application/pdf')) {
                        invalidFiles.push(file.name);
                    }
                    
                    // Identify large files for warning
                    if (file.size > 16 * 1024 * 1024 && file.size <= 100 * 1024 * 1024) {
                        largeFiles.push({
                            name: file.name,
                            size: Math.round(file.size / (1024 * 1024) * 10) / 10
                        });
                    }
                    
                    // Check for oversized files
                    if (file.size > 100 * 1024 * 1024) {
                        invalidFiles.push(`${file.name} (exceeds 100MB)`);
                    }
                });
                
                // Show error for invalid files
                if (invalidFiles.length > 0) {
                    const errorMsg = document.createElement('div');
                    errorMsg.id = 'files-error';
                    errorMsg.classList.add('alert', 'alert-danger', 'mt-2');
                    
                    if (invalidFiles.length === 1) {
                        errorMsg.textContent = `Invalid file: ${invalidFiles[0]}. Only PDF files under 100MB are allowed.`;
                    } else {
                        errorMsg.innerHTML = `Invalid files detected:<ul>` + 
                            invalidFiles.map(f => `<li>${f}</li>`).join('') + 
                            `</ul>Only PDF files under 100MB are allowed.`;
                    }
                    
                    filesInput.parentNode.appendChild(errorMsg);
                    
                    // Don't clear the entire selection - let the user decide what to do
                    // They may want to keep some of the valid files
                }
                
                // Show warning for large files
                if (largeFiles.length > 0 && invalidFiles.length === 0) {
                    const warningMsg = document.createElement('div');
                    warningMsg.id = 'files-warning';
                    warningMsg.classList.add('alert', 'alert-warning', 'mt-2');
                    
                    if (largeFiles.length === 1) {
                        warningMsg.innerHTML = `Large file detected: <strong>${largeFiles[0].name} (${largeFiles[0].size} MB)</strong>. ` + 
                            `Chunked upload will be used to handle this file reliably.`;
                    } else {
                        warningMsg.innerHTML = `Large files detected:<ul>` + 
                            largeFiles.map(f => `<li><strong>${f.name} (${f.size} MB)</strong></li>`).join('') + 
                            `</ul>Chunked upload will be used to handle these files reliably.`;
                    }
                    
                    filesInput.parentNode.appendChild(warningMsg);
                    
                    // Show the progress container (it will be populated during upload)
                    const progressContainer = document.getElementById('upload-progress-container');
                    if (progressContainer) {
                        progressContainer.style.display = 'block';
                    }
                }
            }
        });
    }
    
    // Chunked file upload functionality
    const uploadForm = document.querySelector('form[action="/upload"]');
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            const fileInput = document.getElementById('files');
            const files = fileInput?.files;
            const contentType = document.querySelector('input[name="content_type"]:checked')?.value;
            
            // Only apply chunked upload for PDF content type
            if (contentType === 'pdf' && files && files.length > 0) {
                const largeFiles = Array.from(files).filter(file => file.size > 16 * 1024 * 1024);
                
                // If there are large files (>16MB), use chunked upload
                if (largeFiles.length > 0) {
                    e.preventDefault(); // Stop normal form submission
                    
                    // Create progress container if it doesn't exist
                    let progressContainer = document.getElementById('upload-progress-container');
                    if (!progressContainer) {
                        progressContainer = document.createElement('div');
                        progressContainer.id = 'upload-progress-container';
                        progressContainer.classList.add('mt-4');
                        uploadForm.appendChild(progressContainer);
                    } else {
                        progressContainer.innerHTML = ''; // Clear existing progress elements
                    }
                    
                    // Track uploads
                    let completedUploads = 0;
                    let failedUploads = 0;
                    let totalUploads = largeFiles.length;
                    
                    // Disable submit button during upload
                    const submitBtn = uploadForm.querySelector('button[type="submit"]');
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Uploading...';
                    
                    // Add status message
                    const statusMsg = document.createElement('div');
                    statusMsg.classList.add('alert', 'alert-info');
                    statusMsg.innerHTML = '<strong>Processing large files using chunked upload</strong><p>Please wait while your files are being uploaded...</p>';
                    progressContainer.appendChild(statusMsg);
                    
                    // Process each large file
                    largeFiles.forEach(file => {
                        // Create a progress element for this file
                        const progressElement = document.createElement('div');
                        progressElement.classList.add('progress', 'mb-3');
                        progressElement.style.height = '25px';
                        
                        const progressBar = document.createElement('div');
                        progressBar.classList.add('progress-bar', 'progress-bar-striped', 'progress-bar-animated');
                        progressBar.style.width = '0%';
                        progressBar.setAttribute('aria-valuenow', '0');
                        progressBar.setAttribute('aria-valuemin', '0');
                        progressBar.setAttribute('aria-valuemax', '100');
                        progressBar.textContent = `${file.name} (0%)`;
                        
                        progressElement.appendChild(progressBar);
                        progressContainer.appendChild(progressElement);
                        
                        // Upload the file using chunked upload
                        uploadLargeFileInChunks(file, progressBar, statusMsg)
                            .then(response => {
                                completedUploads++;
                                checkAllUploadsComplete();
                            })
                            .catch(error => {
                                failedUploads++;
                                progressBar.classList.remove('progress-bar-animated');
                                progressBar.classList.add('bg-danger');
                                progressBar.textContent = `${file.name} - Failed: ${error}`;
                                checkAllUploadsComplete();
                            });
                    });
                    
                    // Function to check if all uploads are complete
                    function checkAllUploadsComplete() {
                        if (completedUploads + failedUploads === totalUploads) {
                            // Re-enable submit button
                            submitBtn.disabled = false;
                            submitBtn.innerHTML = 'Upload Document';
                            
                            // Show completion message
                            statusMsg.classList.remove('alert-info');
                            if (failedUploads === 0) {
                                statusMsg.classList.add('alert-success');
                                statusMsg.innerHTML = '<strong>Upload Complete!</strong><p>All files were successfully processed.</p>';
                                
                                // Redirect to library
                                window.location.href = '/library';
                            } else {
                                statusMsg.classList.add('alert-warning');
                                statusMsg.innerHTML = `<strong>Upload Partially Complete</strong><p>${completedUploads} of ${totalUploads} files were uploaded successfully. ${failedUploads} files failed.</p>`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    /**
     * Upload a large file in chunks to avoid server timeout issues
     * @param {File} file - The file to upload
     * @param {HTMLElement} progressBar - Progress bar element to update
     * @param {HTMLElement} statusElement - Status message element to update
     * @returns {Promise} - Promise that resolves when upload is complete
     */
    function uploadLargeFileInChunks(file, progressBar, statusElement) {
        return new Promise((resolve, reject) => {
            const chunkSize = 2 * 1024 * 1024; // 2MB chunks
            const totalChunks = Math.ceil(file.size / chunkSize);
            const uploadId = Date.now().toString() + '-' + Math.random().toString(36).substring(2, 15);
            let currentChunk = 0;
            
            // Get form data values
            const category = document.querySelector('select[name="category"]')?.value || 'Uncategorized';
            
            // Function to upload a single chunk
            function uploadChunk() {
                const start = currentChunk * chunkSize;
                const end = Math.min(file.size, start + chunkSize);
                const chunk = file.slice(start, end);
                
                // Create FormData object for this chunk
                const formData = new FormData();
                formData.append('chunk', chunk);
                formData.append('chunk_number', currentChunk);
                formData.append('total_chunks', totalChunks);
                formData.append('filename', file.name);
                formData.append('upload_id', uploadId);
                formData.append('category', category);
                
                // Update status
                statusElement.innerHTML = `<strong>Uploading file: ${file.name}</strong><p>Uploading chunk ${currentChunk + 1} of ${totalChunks}</p>`;
                
                // Send chunk to server
                fetch('/chunked_upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        return response.json().then(data => {
                            throw new Error(data.message || `Server error: ${response.status}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    // Update progress bar
                    const percentComplete = ((currentChunk + 1) / totalChunks) * 100;
                    progressBar.style.width = `${percentComplete}%`;
                    progressBar.setAttribute('aria-valuenow', percentComplete);
                    progressBar.textContent = `${file.name} (${Math.round(percentComplete)}%)`;
                    
                    // Check if we're done or should proceed with next chunk
                    if (currentChunk < totalChunks - 1) {
                        // Process next chunk
                        currentChunk++;
                        uploadChunk();
                    } else {
                        // All chunks uploaded
                        progressBar.classList.remove('progress-bar-animated');
                        progressBar.classList.add('bg-success');
                        progressBar.textContent = `${file.name} - Upload Complete!`;
                        
                        // If the server returned a document ID, we can add a link to view it
                        if (data.document_id) {
                            const viewLink = document.createElement('a');
                            viewLink.href = `/document/${data.document_id}`;
                            viewLink.classList.add('btn', 'btn-sm', 'btn-success', 'ms-2');
                            viewLink.textContent = 'View Document';
                            progressBar.parentNode.appendChild(viewLink);
                        }
                        
                        // Check if badges were earned
                        if (data.badges_earned && data.badges_earned.length > 0) {
                            const badgesList = document.createElement('div');
                            badgesList.classList.add('alert', 'alert-success', 'mt-2');
                            badgesList.innerHTML = '<strong>Badges Earned:</strong><ul>';
                            
                            data.badges_earned.forEach(badge => {
                                badgesList.innerHTML += `<li>${badge.name} badge (${badge.level})</li>`;
                            });
                            
                            badgesList.innerHTML += '</ul>';
                            progressBar.parentNode.appendChild(badgesList);
                        }
                        
                        resolve(data);
                    }
                })
                .catch(error => {
                    console.error('Error uploading chunk:', error);
                    reject(error.message || 'Upload failed');
                });
            }
            
            // Start uploading the first chunk
            uploadChunk();
        });
    }
    
    // Handle search form validation for forms not already having handlers
    // Skip #searchForm and #searchResultsForm since they already have handlers for the overlay
    const searchForms = document.querySelectorAll('form[action*="search"]:not(#searchForm):not(#searchResultsForm)');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const searchInput = this.querySelector('input[name="query"]');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                
                // Create error message if it doesn't exist
                let errorMsg = this.querySelector('.search-error');
                if (!errorMsg) {
                    errorMsg = document.createElement('div');
                    errorMsg.classList.add('search-error', 'alert', 'alert-danger', 'mt-2');
                    searchInput.parentNode.appendChild(errorMsg);
                }
                
                errorMsg.textContent = 'Please enter a search term';
                searchInput.focus();
            }
        });
    });
    
    // Automatically open the first result on search results page
    const firstAccordionButton = document.querySelector('.accordion-button');
    if (firstAccordionButton && window.location.pathname.includes('/search')) {
        setTimeout(() => {
            firstAccordionButton.click();
        }, 500);
    }
    
    // Rotating example questions in search box placeholder
    const searchInput = document.querySelector('input[name="query"]');
    if (searchInput) {
        // Example questions organized by categories
        const exampleQuestions = {
            // Industry Insights related questions
            industryInsights: [
                "What are the latest trends in customer service technology?",
                "How is AI transforming the customer support industry?",
                "What metrics are most important for measuring customer satisfaction?",
                "What challenges do financial service companies face with digital engagement?",
                "How are companies adapting to remote customer service operations?"
            ],
            
            // Technology News related questions
            technologyNews: [
                "What are the most promising technologies for customer service in 2025?",
                "How are companies implementing chatbots effectively?",
                "What security concerns exist with customer data management?",
                "How is blockchain being used in customer service applications?",
                "What's the impact of voice recognition technology on customer experience?"
            ],
            
            // Product Management related questions
            productManagement: [
                "What methodologies work best for customer-centric product development?",
                "How to prioritize features for a customer service platform?",
                "What KPIs should product managers track for service applications?",
                "How to incorporate customer feedback into product roadmaps?",
                "What's the best approach to launching a new service feature?"
            ],
            
            // Customer Service related questions
            customerService: [
                "What are best practices for reducing customer wait times?",
                "How to improve first-call resolution rates?",
                "What training methods work best for customer service representatives?",
                "How to balance automation with human touch in customer service?",
                "What are effective strategies for handling difficult customers?"
            ],
            
            // Team-specific questions
            teamSpecific: {
                // Digital Engagement
                "Digital Engagement": [
                    "How to optimize customer engagement across digital channels?",
                    "What metrics best measure digital customer engagement success?",
                    "How to personalize digital customer interactions at scale?"
                ],
                
                // Digital Product
                "Digital Product": [
                    "What frameworks help prioritize digital product features?",
                    "How to balance UX and technical constraints in digital products?",
                    "What are best practices for digital product testing and validation?"
                ],
                
                // NextGen Products
                "NextGen Products": [
                    "How are emerging technologies shaping next-generation products?",
                    "What methodologies best support innovation in product development?",
                    "How to identify opportunities for disruptive product innovation?"
                ],
                
                // Product Insights
                "Product Insights": [
                    "What data sources provide the most valuable product insights?",
                    "How to effectively translate customer feedback into product improvements?",
                    "What tools best support product analytics and measurement?"
                ],
                
                // Product Testing
                "Product Testing": [
                    "What are the most effective methods for usability testing?",
                    "How to design test cases that uncover critical product issues?",
                    "What metrics best indicate product quality and reliability?"
                ],
                
                // Service Technology
                "Service Technology": [
                    "What technologies are most effective for improving service efficiency?",
                    "How to evaluate new service technology investments?",
                    "What service technologies have the highest ROI in customer satisfaction?"
                ]
            },
            
            // Short searchable terms in question format
            shortTerms: [
                "What are the latest CRM trends?",
                "How can I measure chatbot ROI?",
                "How to analyze customer feedback effectively?",
                "What are best practices for service automation?",
                "How to improve agent productivity?",
                "Which digital engagement metrics matter most?",
                "How can self-service portals reduce support costs?",
                "How is voice recognition changing customer service?",
                "What insights can AI provide about customers?",
                "How to implement effective omnichannel support?",
                "Which call center metrics should I track?",
                "What are effective customer retention strategies?",
                "How to calculate service technology ROI?",
                "How can support ticket analysis improve service?"
            ]
        };
        
        // Combine all categories into a single array
        let allQuestions = [
            ...exampleQuestions.industryInsights,
            ...exampleQuestions.technologyNews,
            ...exampleQuestions.productManagement,
            ...exampleQuestions.customerService,
            ...exampleQuestions.shortTerms
        ];
        
        // Add team-specific questions
        Object.values(exampleQuestions.teamSpecific).forEach(questions => {
            allQuestions = allQuestions.concat(questions);
        });
        
        // Shuffle the questions array for randomness
        const shuffleArray = (array) => {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        };
        
        // Shuffle the questions
        const shuffledQuestions = shuffleArray([...allQuestions]);
        let currentQuestionIndex = 0;
        
        // Function to update the placeholder text
        const updatePlaceholder = () => {
            searchInput.setAttribute('placeholder', shuffledQuestions[currentQuestionIndex]);
            currentQuestionIndex = (currentQuestionIndex + 1) % shuffledQuestions.length;
        };
        
        // Set initial placeholder
        updatePlaceholder();
        
        // Change placeholder text every 5 seconds
        setInterval(updatePlaceholder, 5000);
        
        // Reset placeholder when input is focused
        searchInput.addEventListener('focus', function() {
            this.setAttribute('placeholder', 'Ask a question or search for keywords...');
        });
        
        // Restore rotating placeholders when input is blurred and empty
        searchInput.addEventListener('blur', function() {
            if (!this.value.trim()) {
                updatePlaceholder();
            }
        });
        
        // Add example search lozenges/buttons beneath the search box
        const exampleSearchesContainer = document.getElementById('exampleSearches');
        if (exampleSearchesContainer) {
            // Select 3 random examples from the shuffled questions to display as clickable lozenges
            // Prefer shorter examples for better UI (using shortTerms array preferentially)
            const selectExampleSearches = () => {
                // Start with short terms
                const shortExamples = shuffleArray([...exampleQuestions.shortTerms]);
                
                // Get 3 examples - prefer short terms but fall back to other examples if needed
                const selectedExamples = shortExamples.slice(0, 3);
                
                // Add to example searches container
                exampleSearchesContainer.innerHTML = '';
                
                selectedExamples.forEach(example => {
                    const button = document.createElement('a');
                    button.href = `search?query=${encodeURIComponent(example)}`;
                    button.classList.add('btn', 'btn-sm', 'btn-outline-info', 'rounded-pill', 'me-2', 'mb-2', 'no-md-convert');
                    
                    // Add icon based on the type of example
                    if (exampleQuestions.industryInsights.includes(example)) {
                        button.innerHTML = `<i class="fas fa-chart-line me-1"></i> ${example}`;
                    } else if (exampleQuestions.technologyNews.includes(example)) {
                        button.innerHTML = `<i class="fas fa-microchip me-1"></i> ${example}`;
                    } else if (exampleQuestions.productManagement.includes(example)) {
                        button.innerHTML = `<i class="fas fa-tasks me-1"></i> ${example}`;
                    } else if (exampleQuestions.customerService.includes(example)) {
                        button.innerHTML = `<i class="fas fa-headset me-1"></i> ${example}`;
                    } else {
                        button.innerHTML = `<i class="fas fa-search me-1"></i> ${example}`;
                    }
                    
                    // Add direct onclick handler to ensure navigation works and show loading indicator
                    button.onclick = function(e) {
                        e.preventDefault();
                        console.log('Homepage search button clicked - adding robot animation');
                        
                        // Set the search input value to the example text
                        const mainSearchInput = document.getElementById('mainSearchInput');
                        if (mainSearchInput) {
                            mainSearchInput.value = example;
                        }
                        
                        // Immediately change this button's appearance with animation
                        this.classList.add('active', 'disabled', 'example-active');
                        // Replace with animated robot icon
                        this.innerHTML = `<i class="fas fa-robot fa-bounce me-1"></i> ${example}`;
                        console.log('Applied robot icon animation to button:', this.innerHTML);
                        
                        // Force a reflow to apply new styles immediately
                        void this.offsetWidth;
                        
                        // Make other example buttons appear disabled
                        const exampleButtons = this.parentElement.querySelectorAll('a.btn');
                        exampleButtons.forEach(btn => {
                            if (btn !== this) {
                                btn.classList.add('disabled');
                                btn.style.opacity = '0.5';
                            }
                        });
                        
                        // Show the full-screen search overlay with animation
                        const searchInProgressOverlay = document.getElementById('searchInProgressOverlay');
                        console.log('Search overlay element:', searchInProgressOverlay);
                        
                        if (searchInProgressOverlay) {
                            // Update the query text
                            const searchQueryElement = searchInProgressOverlay.querySelector('.search-query');
                            if (searchQueryElement) {
                                searchQueryElement.textContent = `"${example}"`;
                                console.log('Set search query text:', example);
                            }
                            
                            // Show the overlay
                            searchInProgressOverlay.classList.add('visible');
                            console.log('Added visible class to overlay');
                            
                            // Force display style
                            searchInProgressOverlay.style.display = 'flex';
                            searchInProgressOverlay.style.opacity = '1';
                            searchInProgressOverlay.style.visibility = 'visible';
                            console.log('Forced styles on overlay');
                        } else {
                            console.error('Search overlay element not found!');
                        }
                        
                        // Check if we're on the homepage
                        const isHomepage = window.location.pathname === '/' || window.location.pathname === '';
                        
                        // Update search form UI for visual feedback
                        const searchContainer = document.getElementById('searchContainer');
                        const searchCard = document.querySelector('.search-container');
                        const mainSearchButton = document.getElementById('mainSearchButton');
                        const mainSearchSpinner = document.getElementById('mainSearchSpinner');
                        const mainSearchSpinnerInline = document.getElementById('mainSearchSpinnerInline');
                        
                        // Show AI search overlay if available
                        if (typeof window.showAISearchOverlay === 'function') {
                            window.showAISearchOverlay(example);
                        } else {
                            // Apply visual search indicator styles
                            if (searchContainer) {
                                searchContainer.classList.add('searching');
                            }
                            
                            if (searchCard) {
                                searchCard.classList.add('searching');
                            }
                            
                            // Show spinner
                            if (mainSearchSpinner) {
                                mainSearchSpinner.classList.remove('d-none');
                            }
                            
                            // Update search button appearance
                            if (mainSearchButton) {
                                mainSearchButton.disabled = true;
                                mainSearchButton.classList.add('btn-warning');
                                mainSearchButton.classList.remove('btn-primary');
                                
                                // Show spinner in button
                                const searchButtonNormal = mainSearchButton.querySelector('.search-button-normal');
                                if (searchButtonNormal) {
                                    searchButtonNormal.classList.add('d-none');
                                }
                                if (mainSearchSpinnerInline) {
                                    mainSearchSpinnerInline.classList.remove('d-none');
                                }
                            }
                        }
                        
                        // Force browser to perform layout/paint before navigating
                        // This ensures animations are visible
                        setTimeout(() => {
                            // Create a visual flash effect on the search box to highlight it's active
                            if (searchContainer) {
                                searchContainer.style.transition = 'all 0.2s ease';
                                searchContainer.style.backgroundColor = 'rgba(var(--bs-warning-rgb), 0.2)';
                                
                                setTimeout(() => {
                                    searchContainer.style.backgroundColor = '';
                                }, 200);
                            }
                            
                            // FINALLY navigate after all animations have had time to display
                            setTimeout(() => {
                                console.log('NAVIGATION HAPPENING NOW');
                                window.location.href = this.href;
                            }, 3000); // Much longer delay to ensure visibility of overlay (3 seconds)
                        }, 100);
                        
                        return false;
                    };
                    
                    exampleSearchesContainer.appendChild(button);
                });
            };
            
            // Set initial examples
            selectExampleSearches();
        }
    }
    
    // Also add example searches to search results page
    const searchResultsExamplesContainer = document.getElementById('searchResultsExamples');
    if (searchResultsExamplesContainer) {
        // Function to shuffle an array
        const shuffleArray = (array) => {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
            return array;
        };
        
        // Function to update search examples in the UI
        function updateSearchExamples(examplesList) {
            if (!searchResultsExamplesContainer) return;
            
            // Clear the container
            searchResultsExamplesContainer.innerHTML = '';
            
            // Select 3 random examples
            const selectedExamples = shuffleArray([...examplesList]).slice(0, 3);
            
            // Add new examples
            selectedExamples.forEach(example => {
                const button = document.createElement('a');
                button.href = `search?query=${encodeURIComponent(example)}`;
                button.classList.add('btn', 'btn-sm', 'btn-outline-info', 'rounded-pill', 'me-2', 'mb-2', 'no-md-convert');
                button.innerHTML = `<i class="fas fa-search me-1"></i> ${example}`;
                
                // Add direct onclick handler to ensure navigation works
                button.onclick = function(e) {
                    // Show AI-specific loading indicator
                    e.preventDefault();
                    
                    // Set input field value to match example search
                    const mainSearchInput = document.getElementById('mainSearchInput');
                    const searchResultsInput = document.getElementById('searchResultsInput');
                    if (mainSearchInput) mainSearchInput.value = example;
                    if (searchResultsInput) searchResultsInput.value = example;
                    
                    // Show the full-screen search overlay with animation
                    const searchInProgressOverlay = document.getElementById('searchInProgressOverlay');
                    console.log('Search results page - overlay element:', searchInProgressOverlay);
                    
                    if (searchInProgressOverlay) {
                        // Update the query text
                        const searchQueryElement = searchInProgressOverlay.querySelector('.search-query');
                        if (searchQueryElement) {
                            searchQueryElement.textContent = `"${example}"`;
                            console.log('Search results page - set query text:', example);
                        }
                        
                        // Show the overlay
                        searchInProgressOverlay.classList.add('visible');
                        console.log('Search results page - added visible class');
                        
                        // Force display style
                        searchInProgressOverlay.style.display = 'flex';
                        searchInProgressOverlay.style.opacity = '1';
                        searchInProgressOverlay.style.visibility = 'visible';
                        console.log('Search results page - forced styles');
                    } else {
                        console.error('Search results page - overlay element not found!');
                    }
                    
                    // Determine which page we're on
                    const isHomepage = window.location.pathname === '/' || window.location.pathname === '';
                    const isSearchPage = window.location.pathname === '/search';
                    
                    // Use the global search overlay function if available
                    if (window.showAISearchOverlay) {
                        window.showAISearchOverlay(example);
                    } else {
                        // Enhanced loading indicators for search buttons
                        const mainSearchButton = document.getElementById('mainSearchButton');
                        const mainSearchSpinner = document.getElementById('mainSearchSpinner');
                        const mainSearchSpinnerInline = document.getElementById('mainSearchSpinnerInline');
                        const searchResultsButton = document.getElementById('searchResultsButton');
                        const searchResultsSpinner = document.getElementById('searchSpinner');
                        const searchResultsSpinnerInline = document.getElementById('searchResultsSpinnerInline');
                        
                        // Apply loading states based on which page we're on
                        if (isHomepage || !isSearchPage) {
                            // On homepage or non-search pages
                            if (mainSearchButton) {
                                // Update button state with inline spinner
                                mainSearchButton.disabled = true;
                                mainSearchButton.classList.add('btn-warning');
                                mainSearchButton.classList.remove('btn-primary');
                                
                                // Show spinner in button
                                const searchButtonNormal = mainSearchButton.querySelector('.search-button-normal');
                                if (searchButtonNormal) searchButtonNormal.classList.add('d-none');
                                if (mainSearchSpinnerInline) mainSearchSpinnerInline.classList.remove('d-none');
                                
                                // Add searching class to container
                                const searchContainer = document.getElementById('searchContainer');
                                if (searchContainer) searchContainer.classList.add('searching');
                            }
                            if (mainSearchSpinner) mainSearchSpinner.classList.remove('d-none');
                        } else {
                            // On search results page
                            if (searchResultsButton) {
                                // Update button state with inline spinner
                                searchResultsButton.disabled = true;
                                searchResultsButton.classList.add('btn-warning');
                                searchResultsButton.classList.remove('btn-primary');
                                
                                // Show spinner in button
                                const searchButtonNormal = searchResultsButton.querySelector('.search-button-normal');
                                if (searchButtonNormal) searchButtonNormal.classList.add('d-none');
                                if (searchResultsSpinnerInline) searchResultsSpinnerInline.classList.remove('d-none');
                                
                                // Add searching class to container
                                const searchContainer = document.querySelector('.search-container');
                                if (searchContainer) searchContainer.classList.add('searching');
                            }
                            if (searchResultsSpinner) searchResultsSpinner.classList.remove('d-none');
                        }
                    }
                    
                    // Change button appearance with animation
                    button.classList.add('active', 'disabled', 'example-active');
                    // Replace icon with animated robot icon
                    button.innerHTML = `<i class="fas fa-robot fa-bounce me-1"></i> ${example}`;
                    
                    // Force a reflow to apply new styles immediately
                    void button.offsetWidth;
                    
                    // Mark other example buttons as inactive
                    const exampleButtons = button.parentElement.querySelectorAll('a.btn');
                    exampleButtons.forEach(btn => {
                        if (btn !== button) {
                            btn.classList.add('disabled');
                            btn.style.opacity = '0.5';
                        }
                    });
                    
                    // Force browser to perform layout/paint before navigating
                    // This ensures animations are visible
                    setTimeout(() => {
                        // Create a visual flash effect on the search box
                        const searchContainer = document.querySelector('.search-container');
                        if (searchContainer) {
                            searchContainer.style.transition = 'all 0.2s ease';
                            searchContainer.style.backgroundColor = 'rgba(var(--bs-warning-rgb), 0.2)';
                            
                            setTimeout(() => {
                                searchContainer.style.backgroundColor = '';
                            }, 200);
                        }
                        
                        // FINALLY navigate after all animations have had time to display
                        setTimeout(() => {
                            console.log('SEARCH RESULTS PAGE - NAVIGATION HAPPENING NOW');
                            window.location.href = this.href;
                        }, 3000); // Much longer delay for overlay visibility (3 seconds)
                    }, 100);
                    
                    return false;
                };
                
                searchResultsExamplesContainer.appendChild(button);
            });
        }
        
        // Initial placeholder examples
        let initialExamples = ["Loading topics...", "Please wait..."];
        updateSearchExamples(initialExamples);
        
        // Try to fetch real document topics from our API
        fetch('/api/document-topics')
            .then(response => response.json())
            .then(data => {
                if (data && data.topics && data.topics.length > 0) {
                    // Use the fetched topics
                    updateSearchExamples(data.topics);
                } else {
                    throw new Error('No topics returned from API');
                }
            })
            .catch(error => {
                console.warn('Error fetching document topics:', error);
                // Fallback to question-based examples based on actual document content
                const fallbackExamples = [
                    "What are AI agents?",
                    "How does augmented reality improve productivity?",
                    "What are the latest customer service trends?",
                    "How can digital transformation help my business?",
                    "What is the future of customer management?",
                    "How are companies using generative AI?",
                    "What is sprint planning methodology?",
                    "How to create an effective product roadmap?",
                    "How does AI provide customer insights?",
                    "What's in the latest Notebook February issue?",
                    "When will AR/VR technology become mainstream?"
                ];
                updateSearchExamples(fallbackExamples);
            });
    }
    
    // Auto-scrolling functionality for latest documents carousel
    const latestRow = document.getElementById('latestDocumentsRow');
    if (latestRow && latestRow.children.length > 1) {
        let scrollPosition = 0;
        const scrollAmount = latestRow.scrollWidth / latestRow.children.length;
        
        // Auto-scroll every 5 seconds
        setInterval(() => {
            scrollPosition += scrollAmount;
            if (scrollPosition >= latestRow.scrollWidth) {
                scrollPosition = 0;
            }
            latestRow.scrollTo({
                left: scrollPosition,
                behavior: 'smooth'
            });
        }, 5000);
    }
});

/**
 * Enhanced search suggestions with dynamic question carousel
 * Replaced voice search with more reliable text-based search
 * Material Design v3 conformant
 * Added auto-scrolling carousel for latest documents
 * Added featured documents section with hover effects
 */
