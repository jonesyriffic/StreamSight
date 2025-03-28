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
    const pdfObject = document.getElementById('pdf-viewer');
    const downloadLink = document.getElementById('pdf-download-link');
    
    if (!container || !pdfObject) {
        console.error('PDF container or viewer element not found');
        return;
    }
    
    // Set the data attribute of the object to the PDF URL
    pdfObject.setAttribute('data', pdfUrl);
    
    // Set the download link href
    if (downloadLink) {
        downloadLink.setAttribute('href', pdfUrl);
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
