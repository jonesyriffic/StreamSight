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
    
    // Initialize voice search functionality
    initializeVoiceSearch();

    // File input validation
    const fileInput = document.getElementById('file');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            const fileError = document.getElementById('file-error');
            
            // Remove any existing error message
            if (fileError) {
                fileError.remove();
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
                
                // Check file size (max 16MB)
                else if (file.size > 16 * 1024 * 1024) {
                    const errorMsg = document.createElement('div');
                    errorMsg.id = 'file-error';
                    errorMsg.classList.add('alert', 'alert-danger', 'mt-2');
                    errorMsg.textContent = 'File size must be less than 16MB';
                    fileInput.parentNode.appendChild(errorMsg);
                    fileInput.value = '';
                }
            }
        });
    }
    
    // Handle search form validation
    const searchForm = document.querySelector('form[action*="search"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
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
    }
    
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
            
            // Short searchable terms
            shortTerms: [
                "CRM trends",
                "Chatbot ROI",
                "Customer feedback analysis",
                "Service automation",
                "Agent productivity",
                "Digital engagement metrics",
                "Self-service portals",
                "Voice recognition",
                "AI customer insights",
                "Omnichannel support",
                "Call center metrics",
                "Customer retention strategies",
                "Service technology ROI",
                "Support ticket analysis"
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
                    
                    // Add direct onclick handler to ensure navigation works
                    button.onclick = function(e) {
                        e.preventDefault();
                        window.location.href = this.href;
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
                    
                    // Determine which page we're on
                    const isHomepage = window.location.pathname === '/' || window.location.pathname === '';
                    
                    // Create and show a more prominent AI loading indicator 
                    // (we'll place this in the fixed container)
                    let loadingDiv = document.createElement('div');
                    loadingDiv.className = 'search-loading-indicator';
                    loadingDiv.innerHTML = `
                      <div class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center" 
                           style="background-color: rgba(0,0,0,0.5); z-index: 9999;">
                        <div class="card p-4 shadow-lg" style="max-width: 500px;">
                          <div class="text-center mb-3">
                            <div class="spinner-border text-info" style="width: 3rem; height: 3rem;" role="status">
                              <span class="visually-hidden">Searching...</span>
                            </div>
                            <div class="mt-3 mb-2">
                              <i class="fas fa-robot text-info fa-2x fa-bounce"></i>
                            </div>
                          </div>
                          <h4 class="text-center">AI Search in Progress</h4>
                          <p class="text-center mb-0">
                            Searching for <strong>"${example}"</strong> across all documents... 
                          </p>
                          <p class="text-center text-muted small mt-2">
                            <i class="fas fa-info-circle me-1"></i>
                            This AI-powered search may take a few moments
                          </p>
                        </div>
                      </div>
                    `;
                    
                    document.body.appendChild(loadingDiv);
                    
                    // Change button appearance
                    button.innerHTML = `<i class="fas fa-robot fa-bounce me-1"></i> ${example}`;
                    button.classList.add('disabled');
                    
                    // Navigate after delay for visual feedback
                    setTimeout(() => {
                        window.location.href = this.href;
                    }, 1200); // Longer delay to show the AI is thinking
                    
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
            .then(topics => {
                if (topics && topics.length > 0) {
                    // Use the fetched topics
                    updateSearchExamples(topics);
                }
            })
            .catch(error => {
                console.warn('Error fetching document topics:', error);
                // Fallback to static examples
                const fallbackExamples = [
                    "CRM trends",
                    "Chatbot ROI",
                    "Customer feedback analysis",
                    "Service automation",
                    "Agent productivity",
                    "Digital engagement metrics",
                    "Self-service portals",
                    "Voice recognition",
                    "AI customer insights",
                    "Omnichannel support",
                    "Call center metrics",
                    "Customer retention strategies",
                    "Service technology ROI",
                    "Support ticket analysis"
                ];
                updateSearchExamples(fallbackExamples);
            });
    }
});

/**
 * Voice Search functionality
 * Uses the Web Speech API for speech recognition
 */
function initializeVoiceSearch() {
    // Get all voice search buttons
    const voiceButtons = document.querySelectorAll('[id^="voiceSearch"]');
    
    // Function to disable voice search and show fallback UI
    const disableVoiceSearch = (message) => {
        console.warn(message);
        voiceButtons.forEach(button => {
            // Change button appearance instead of hiding
            button.innerHTML = '<i class="fas fa-keyboard"></i>';
            button.title = "Voice search not available - use keyboard instead";
            button.disabled = true;
            button.classList.remove('btn-info');
            button.classList.add('btn-secondary');
            
            // Add a message near the search box
            const searchContainer = button.closest('.input-group');
            if (searchContainer && !searchContainer.querySelector('.voice-search-unavailable')) {
                const unavailableMessage = document.createElement('small');
                unavailableMessage.classList.add('text-muted', 'mt-1', 'd-block', 'voice-search-unavailable');
                unavailableMessage.innerHTML = 'Voice search is not currently available.';
                searchContainer.parentNode.appendChild(unavailableMessage);
            }
        });
    };
    
    // Check if browser supports speech recognition
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        disableVoiceSearch('Speech recognition not supported in this browser');
        return;
    }
    
    // Check if we're in a Replit/iframe environment - these often have issues with Web Speech API
    const isReplit = window.location.hostname.includes('replit') || 
                    window.location.hostname.includes('repl.co') ||
                    (window.top !== window.self); // Check if in an iframe
                    
    if (isReplit) {
        disableVoiceSearch('Speech recognition may not work reliably in this environment');
        return;
    }

    // Set up speech recognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    
    // Set up supported languages with fallback mechanism
    try {
        // Common supported languages for speech recognition
        const supportedLanguages = [
            'en-US', 'en-GB', 'en', 
            'fr-FR', 'fr',
            'es-ES', 'es',
            'de-DE', 'de',
            'it-IT', 'it',
            'ja-JP', 'ja',
            'ko-KR', 'ko',
            'pt-BR', 'pt',
            'zh-CN', 'zh'
        ];
        
        // Get browser's language preference
        let browserLang = navigator.language || 'en';
        let langCode = browserLang.split('-')[0]; // Get the base language code (en, fr, etc.)
        
        // Try to find an exact match first
        if (supportedLanguages.includes(browserLang)) {
            recognition.lang = browserLang;
            console.log('Using exact language match:', browserLang);
        } 
        // Then try the base language code
        else if (supportedLanguages.includes(langCode)) {
            recognition.lang = langCode;
            console.log('Using base language match:', langCode);
        }
        // Fallback to English
        else {
            recognition.lang = 'en';
            console.log('Using fallback language: en');
        }
    } catch (error) {
        console.warn('Error setting language, using default:', error);
        recognition.lang = 'en'; // Fallback to generic English without region
    }

    // Set up voice search for main search box on homepage
    setupVoiceSearch(
        'voiceSearchButton', 
        'mainSearchInput', 
        'voiceSearchFeedback',
        'voiceSearchText',
        recognition
    );
    
    // Set up voice search for search results page
    setupVoiceSearch(
        'voiceSearchResultsButton', 
        'searchResultsInput', 
        'voiceSearchResultsFeedback',
        'voiceSearchResultsText',
        recognition
    );
}

/**
 * Set up voice search for a specific button and input field
 */
function setupVoiceSearch(buttonId, inputId, feedbackId, textId, recognition) {
    const voiceButton = document.getElementById(buttonId);
    const searchInput = document.getElementById(inputId);
    const feedbackElement = document.getElementById(feedbackId);
    const textElement = document.getElementById(textId);
    
    // Only proceed if the elements exist
    if (!voiceButton || !searchInput || !feedbackElement) {
        return;
    }
    
    let isListening = false;
    
    // Add click event to the voice search button
    voiceButton.addEventListener('click', function() {
        if (isListening) {
            recognition.stop();
            return;
        }
        
        // Start listening
        try {
            recognition.start();
            isListening = true;
            
            // Update button appearance
            voiceButton.classList.remove('btn-info');
            voiceButton.classList.add('btn-danger');
            voiceButton.innerHTML = '<i class="fas fa-microphone-slash"></i>';
            
            // Show feedback
            feedbackElement.classList.remove('d-none');
            if (textElement) textElement.textContent = '';
        } catch (error) {
            console.error('Error starting speech recognition:', error);
        }
    });
    
    // Handle results from speech recognition
    recognition.onresult = function(event) {
        let interimTranscript = '';
        let finalTranscript = '';
        
        // Collect interim and final transcripts
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        // Update the feedback text with the interim transcript
        if (textElement && interimTranscript) {
            textElement.textContent = interimTranscript;
        }
        
        // If we have a final transcript, update the search input
        if (finalTranscript) {
            searchInput.value = finalTranscript;
        }
    };
    
    // Handle end of speech recognition
    recognition.onend = function() {
        isListening = false;
        
        // Reset button appearance
        voiceButton.classList.remove('btn-danger');
        voiceButton.classList.add('btn-info');
        voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        
        // Hide feedback
        feedbackElement.classList.add('d-none');
        
        // If the search input has a value, submit the form
        if (searchInput.value.trim()) {
            const form = searchInput.closest('form');
            if (form) {
                setTimeout(() => {
                    form.submit();
                }, 500); // Short delay to make sure the user sees the final text
            }
        }
    };
    
    // Handle errors
    recognition.onerror = function(event) {
        console.error('Speech recognition error:', event.error);
        isListening = false;
        
        // Reset button appearance
        voiceButton.classList.remove('btn-danger');
        voiceButton.classList.add('btn-info');
        voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
        
        // Hide feedback
        feedbackElement.classList.add('d-none');
        
        // Create user-friendly error message and handle based on error type
        let errorText = 'Voice recognition error';
        let showFallbackInput = false;
        
        if (event.error === 'language-not-supported') {
            // If language is not supported, try to use a different language next time
            if (recognition.lang !== 'en-US') {
                errorText = `Language "${recognition.lang}" not supported. Switching to English (US) for next attempt.`;
                recognition.lang = 'en-US'; // Try US English next
            } else if (recognition.lang !== 'en') {
                errorText = 'English (US) not supported. Trying generic English for next attempt.';
                recognition.lang = 'en'; // Try generic English next
            } else {
                errorText = 'Speech recognition not supported in this browser environment.';
                showFallbackInput = true; // Show keyboard input instead
            }
        } else if (event.error === 'no-speech') {
            errorText = 'No speech detected. Please try speaking again.';
        } else if (event.error === 'network') {
            errorText = 'Network error occurred. Please check your connection.';
        } else if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
            errorText = 'Microphone access denied. Please allow microphone access.';
            showFallbackInput = true; // Show keyboard input if microphone permission denied
        } else {
            errorText = `Voice recognition error: ${event.error}`;
            showFallbackInput = true; // Show keyboard input for other errors
        }
        
        // Show error message
        const errorMessage = document.createElement('div');
        errorMessage.classList.add('alert', 'alert-warning', 'mt-2');
        errorMessage.innerHTML = `<i class="fas fa-exclamation-triangle me-2"></i>${errorText}`;
        feedbackElement.parentNode.appendChild(errorMessage);
        
        // Create a fallback search box if needed
        if (showFallbackInput) {
            // Don't show fallback if there's already one
            if (!document.getElementById('fallbackSearchContainer')) {
                // Add a typing animation to indicate the transition to keyboard input
                setTimeout(() => {
                    // Create a container for the fallback message and input
                    const fallbackContainer = document.createElement('div');
                    fallbackContainer.id = 'fallbackSearchContainer';
                    fallbackContainer.classList.add('mt-3', 'text-center', 'fade-in');
                    
                    // Add a helpful message
                    const fallbackMessage = document.createElement('div');
                    fallbackMessage.classList.add('mb-2');
                    fallbackMessage.innerHTML = 'Please type your search query instead:';
                    fallbackContainer.appendChild(fallbackMessage);
                    
                    // Focus on the main search input
                    searchInput.focus();
                    
                    // Append the container to the page
                    feedbackElement.parentNode.appendChild(fallbackContainer);
                    
                    // Change the microphone button to a keyboard button
                    voiceButton.innerHTML = '<i class="fas fa-keyboard"></i>';
                    voiceButton.title = "Voice search unavailable - use keyboard input";
                    voiceButton.disabled = true;
                    voiceButton.classList.remove('btn-info');
                    voiceButton.classList.add('btn-secondary');
                }, 1000);
            }
        }
        
        // Remove error message after 8 seconds (longer to give user time to read)
        setTimeout(() => {
            errorMessage.remove();
        }, 8000);
    };
}
