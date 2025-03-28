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
    // Get all PDF related elements
    const pdfViewer = document.getElementById('pdf-viewer');
    const pdfDownloadLink = document.getElementById('pdf-download-link');
    const pdfViewLink = document.getElementById('pdf-view-link');
    const downloadBtn = document.getElementById('download-btn');
    
    // Set the src attribute for the iframe
    if (pdfViewer) {
        pdfViewer.src = pdfUrl;
    }
    
    // Set the href for all PDF links
    if (pdfDownloadLink) {
        pdfDownloadLink.href = pdfUrl;
    }
    
    if (pdfViewLink) {
        pdfViewLink.href = pdfUrl;
    }
    
    // Add event listener for the main download button if it exists
    if (downloadBtn) {
        downloadBtn.addEventListener('click', function() {
            window.location.href = pdfUrl;
        });
    }
    
    console.log('PDF viewer initialized with URL:', pdfUrl);
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
