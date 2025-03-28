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
});
