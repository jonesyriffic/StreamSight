/**
 * Tour management for NextGen Insight Spark onboarding
 */

class OnboardingTour {
    constructor() {
        this.tourConfig = null;
        this.intro = null;
        this.tourInProgress = false;
        this.tourButton = null;
        this.currentStepId = null;
    }

    /**
     * Initialize the tour
     */
    async initialize() {
        try {
            // Fetch the tour configuration from the server
            const response = await fetch('/api/tour/config');
            if (!response.ok) {
                throw new Error('Failed to load tour configuration');
            }
            
            this.tourConfig = await response.json();
            console.log('Tour config loaded:', this.tourConfig);
            
            // Setup the tour button
            this.setupTourButton();
            
            // Check if we should show the tour automatically (first-time users)
            if (this.shouldShowTourAutomatically()) {
                setTimeout(() => this.startTour(), 1500);
            }
        } catch (error) {
            console.error('Error initializing tour:', error);
        }
    }
    
    /**
     * Check if we should show the tour automatically
     */
    shouldShowTourAutomatically() {
        // Only show automatically for authenticated users who haven't completed the tour
        const isAuthenticated = document.body.classList.contains('user-authenticated');
        return isAuthenticated && this.tourConfig && !this.tourConfig.is_complete && !this.getCookie('tour_dismissed');
    }
    
    /**
     * Set up the floating tour button
     */
    setupTourButton() {
        // Check if button already exists
        if (document.getElementById('tour-start-btn')) {
            return;
        }
        
        // Create the button
        this.tourButton = document.createElement('div');
        this.tourButton.id = 'tour-start-btn';
        this.tourButton.className = 'tour-start-btn';
        this.tourButton.innerHTML = '<i class="fas fa-question"></i>';
        this.tourButton.title = 'Start onboarding tour';
        this.tourButton.setAttribute('aria-label', 'Start onboarding tour');
        
        // Add event listener
        this.tourButton.addEventListener('click', () => this.startTour());
        
        // Add to the DOM
        document.body.appendChild(this.tourButton);
    }
    
    /**
     * Prepare tour steps based on configuration
     */
    prepareTourSteps() {
        const steps = [];
        
        // Welcome step
        steps.push({
            element: document.querySelector('header'),
            intro: `<h5>${this.tourConfig.steps.welcome.title}</h5>
                    <p>${this.tourConfig.steps.welcome.content}</p>`,
            position: 'bottom',
            stepId: 'welcome'
        });
        
        // Dashboard step
        const dashboardLink = document.querySelector('a[href="/"]');
        if (dashboardLink) {
            steps.push({
                element: dashboardLink,
                intro: `<h5>${this.tourConfig.steps.dashboard.title}</h5>
                        <p>${this.tourConfig.steps.dashboard.content}</p>`,
                position: 'bottom',
                stepId: 'dashboard'
            });
        }
        
        // Search step
        const searchForm = document.querySelector('form[action="/search"]');
        if (searchForm) {
            steps.push({
                element: searchForm,
                intro: `<h5>${this.tourConfig.steps.search.title}</h5>
                        <p>${this.tourConfig.steps.search.content}</p>`,
                position: 'bottom',
                stepId: 'search'
            });
        }
        
        // Library step
        const libraryLink = document.querySelector('a[href="/library"]');
        if (libraryLink) {
            steps.push({
                element: libraryLink,
                intro: `<h5>${this.tourConfig.steps.library.title}</h5>
                        <p>${this.tourConfig.steps.library.content}</p>`,
                position: 'bottom',
                stepId: 'library'
            });
        }
        
        // Document view step - this might be conditional based on the page
        const documentViewer = document.querySelector('.document-content');
        if (documentViewer) {
            steps.push({
                element: documentViewer,
                intro: `<h5>${this.tourConfig.steps.document_view.title}</h5>
                        <p>${this.tourConfig.steps.document_view.content}</p>`,
                position: 'left',
                stepId: 'document_view'
            });
        }
        
        // Upload step - only if user has permission
        const uploadLink = document.querySelector('a[href="/upload"]');
        if (uploadLink) {
            steps.push({
                element: uploadLink,
                intro: `<h5>${this.tourConfig.steps.upload.title}</h5>
                        <p>${this.tourConfig.steps.upload.content}</p>`,
                position: 'bottom',
                stepId: 'upload'
            });
        }
        
        // Badges step
        const badgesLink = document.querySelector('a[href="/badges"]');
        if (badgesLink) {
            steps.push({
                element: badgesLink,
                intro: `<h5>${this.tourConfig.steps.badges.title}</h5>
                        <p>${this.tourConfig.steps.badges.content}</p>`,
                position: 'left',
                stepId: 'badges'
            });
        }
        
        // Completion step
        steps.push({
            element: document.querySelector('main'),
            intro: `<h5>${this.tourConfig.steps.complete.title}</h5>
                    <p>${this.tourConfig.steps.complete.content}</p>`,
            position: 'middle',
            stepId: 'complete'
        });
        
        return steps;
    }
    
    /**
     * Start the tour
     */
    startTour() {
        if (this.tourInProgress) {
            return;
        }
        
        // Initialize intro.js
        this.intro = introJs();
        
        const steps = this.prepareTourSteps();
        this.intro.setOptions({
            steps: steps,
            showStepNumbers: false,
            showBullets: true,
            showProgress: true,
            disableInteraction: false,
            doneLabel: 'Finish',
            nextLabel: 'Next',
            prevLabel: 'Back',
            exitOnOverlayClick: false,
            tooltipClass: 'tour-tooltip',
            highlightClass: 'tour-highlight'
        });
        
        // Set up event listeners
        this.intro.onbeforechange((targetElement) => {
            const currentStep = this.intro._currentStep;
            if (currentStep < steps.length) {
                this.currentStepId = steps[currentStep].stepId;
            }
        });
        
        this.intro.onchange((targetElement) => {
            // Record step completion for authenticated users
            if (this.currentStepId && document.body.classList.contains('user-authenticated')) {
                this.markStepCompleted(this.currentStepId);
            }
        });
        
        this.intro.oncomplete(() => {
            this.tourInProgress = false;
            
            // Mark the tour as completed for authenticated users
            if (document.body.classList.contains('user-authenticated')) {
                this.markStepCompleted('complete');
            } else {
                // For anonymous users, set a cookie to not show again in this session
                this.setCookie('tour_dismissed', 'true', 1);
            }
        });
        
        this.intro.onexit(() => {
            this.tourInProgress = false;
            
            // For anonymous users, set a cookie to not show again in this session
            if (!document.body.classList.contains('user-authenticated')) {
                this.setCookie('tour_dismissed', 'true', 1);
            }
        });
        
        // Start the tour
        this.tourInProgress = true;
        this.intro.start();
    }
    
    /**
     * Mark a step as completed on the server
     */
    async markStepCompleted(stepId) {
        try {
            const response = await fetch(`/api/tour/step/${stepId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ completed: true })
            });
            
            if (!response.ok) {
                throw new Error('Failed to update tour progress');
            }
            
            const result = await response.json();
            
            // Update our local config
            if (result.success) {
                this.tourConfig = result.tour_config;
            }
        } catch (error) {
            console.error('Error updating tour progress:', error);
        }
    }
    
    /**
     * Reset the tour progress on the server
     */
    async resetTour() {
        try {
            const response = await fetch('/api/tour/reset', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            if (!response.ok) {
                throw new Error('Failed to reset tour progress');
            }
            
            const result = await response.json();
            
            // Update our local config
            if (result.success) {
                this.tourConfig = result.tour_config;
                
                // Start the tour again
                this.startTour();
            }
        } catch (error) {
            console.error('Error resetting tour:', error);
        }
    }
    
    /**
     * Set a cookie
     */
    setCookie(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = `; expires=${date.toUTCString()}`;
        }
        document.cookie = `${name}=${value || ''}${expires}; path=/`;
    }
    
    /**
     * Get a cookie value
     */
    getCookie(name) {
        const nameEQ = `${name}=`;
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) return c.substring(nameEQ.length, c.length);
        }
        return null;
    }
}

// Initialize the tour when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Add flag for checking auth status in the tour
    if (document.querySelector('.navbar [data-bs-target="#userDropdown"]')) {
        document.body.classList.add('user-authenticated');
    }
    
    // Initialize the tour
    window.appTour = new OnboardingTour();
    window.appTour.initialize();
    
    // Add tour reset button functionality if it exists
    const resetTourBtn = document.getElementById('reset-tour-btn');
    if (resetTourBtn) {
        resetTourBtn.addEventListener('click', () => {
            window.appTour.resetTour();
        });
    }
});