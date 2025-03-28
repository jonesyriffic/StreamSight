/**
 * PDF.js initialization for document viewer
 */

// PDF.js worker script
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/pdf.worker.min.js';

/**
 * Initialize the PDF viewer with the given PDF URL
 * @param {string} pdfUrl - URL to the PDF file
 */
function initPdfViewer(pdfUrl) {
    const container = document.getElementById('pdf-container');
    const iframe = document.getElementById('pdf-viewer');
    
    if (!container || !iframe) {
        console.error('PDF container or viewer element not found');
        return;
    }
    
    // Create a URL for the PDF viewer with the PDF URL as a parameter
    const viewerUrl = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.4.120/web/viewer.html?file=${encodeURIComponent(pdfUrl)}`;
    
    // Set the iframe source to the PDF viewer URL
    iframe.src = viewerUrl;
    
    // Add event listener for iframe load
    iframe.addEventListener('load', function() {
        console.log('PDF viewer loaded');
        
        try {
            // Try to access the PDF viewer application inside the iframe
            const pdfViewerApplication = iframe.contentWindow.PDFViewerApplication;
            
            // Make the PDF viewer application available globally for document searching
            window.PDFViewerApplication = pdfViewerApplication;
            
            // Configure PDF viewer options if needed
            if (pdfViewerApplication) {
                pdfViewerApplication.initializedPromise.then(() => {
                    // Set viewer preferences
                    pdfViewerApplication.preferences.set('sidebarViewOnLoad', 2); // Thumbnails sidebar
                    pdfViewerApplication.preferences.set('spreadModeOnLoad', 0); // No spreads
                    pdfViewerApplication.preferences.set('scrollModeOnLoad', 0); // Vertical scrolling
                    
                    console.log('PDF viewer initialized with custom preferences');
                });
            }
        } catch (error) {
            // This might fail due to cross-origin restrictions
            console.warn('Could not access PDF viewer application:', error);
        }
    });
    
    // Handle any errors
    iframe.addEventListener('error', function(error) {
        console.error('Error loading PDF viewer:', error);
        container.innerHTML = `
            <div class="alert alert-danger m-3">
                <strong>Error:</strong> Failed to load PDF viewer. 
                <a href="${pdfUrl}" target="_blank" class="alert-link">Click here to open the PDF directly</a>.
            </div>
        `;
    });
}

/**
 * Extract text from a PDF using PDF.js
 * @param {string} pdfUrl - URL to the PDF file
 * @returns {Promise<string>} - Promise resolving to the extracted text
 */
async function extractTextFromPdf(pdfUrl) {
    try {
        // Load the PDF document
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;
        
        let extractedText = '';
        
        // Loop through each page
        for (let i = 1; i <= pdf.numPages; i++) {
            const page = await pdf.getPage(i);
            const textContent = await page.getTextContent();
            
            // Extract text items
            const textItems = textContent.items.map(item => item.str);
            const pageText = textItems.join(' ');
            
            extractedText += pageText + '\n\n';
        }
        
        return extractedText;
    } catch (error) {
        console.error('Error extracting text from PDF:', error);
        throw error;
    }
}
