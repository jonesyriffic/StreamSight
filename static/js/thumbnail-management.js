// Thumbnail Management JavaScript
$(document).ready(function() {
    // Get document ID from the page
    const docId = document.getElementById('doc-id').value;
    
    // Upload thumbnail
    $('#thumbnail-upload-form').submit(function(e) {
        e.preventDefault();
        
        // Validate file input
        if (!$('#thumbnail')[0].files.length) {
            toastr.error('Please select an image file to upload');
            return;
        }
        
        // Show loading indicator
        const submitBtn = $(this).find('button[type="submit"]');
        const originalText = submitBtn.text();
        submitBtn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...');
        
        // Show the upload info alert
        $('.upload-thumbnail-info').show();
        
        // Get file details for better UX messaging
        const file = $('#thumbnail')[0].files[0];
        const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);
        $('.upload-info').text(`Uploading and processing ${file.name} (${fileSizeMB} MB). This should take only a few seconds.`);
        
        // Create form data
        const formData = new FormData();
        formData.append('thumbnail', file);
        
        // Create a progress timer to update status
        let seconds = 0;
        const progressTimer = setInterval(function() {
            seconds++;
            let status = "Uploading Thumbnail";
            if (seconds > 3) {
                status = "Processing Image...";
            }
            if (seconds > 8) {
                status = "Optimizing Image...";
            }
            if (seconds > 15) {
                status = "Almost Complete...";
            }
            $('.upload-status').text(status);
        }, 1000);
        
        // Send request
        $.ajax({
            url: `/admin/document/${docId}/upload-thumbnail`,
            type: 'POST',
            data: formData,
            contentType: false,
            processData: false,
            success: function(response) {
                // Clear the timer
                clearInterval(progressTimer);
                
                if (response.success) {
                    // Update status
                    $('.upload-status').text("Thumbnail Successfully Uploaded!");
                    $('.upload-thumbnail-info').removeClass('alert-info').addClass('alert-success');
                    $('.upload-progress-container').html('<span class="material-symbols-outlined text-success" style="font-size: 2rem;">check_circle</span>');
                    $('.upload-info').text('Your custom thumbnail has been uploaded and applied to the document.');
                    
                    // Show success message
                    toastr.success(response.message);
                    
                    // Refresh the page after a short delay to show the new thumbnail
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    // Hide the info alert
                    $('.upload-thumbnail-info').hide();
                    
                    // Show error message
                    toastr.error(response.message || 'Failed to upload thumbnail');
                    
                    // Reset button
                    submitBtn.prop('disabled', false).text(originalText);
                }
            },
            error: function(xhr) {
                // Clear the timer
                clearInterval(progressTimer);
                
                // Hide the info alert
                $('.upload-thumbnail-info').hide();
                
                // Show error message
                let errorMessage = 'Failed to upload thumbnail';
                try {
                    errorMessage = JSON.parse(xhr.responseText).message || errorMessage;
                } catch (e) {}
                
                toastr.error(errorMessage);
                
                // Reset button
                submitBtn.prop('disabled', false).text(originalText);
            }
        });
    });
    
    // Generate thumbnail
    $('#btn-generate-thumbnail').click(function() {
        // Show loading indicator
        const btn = $(this);
        const originalText = btn.text();
        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...');
        
        // Show the info alert
        $('.thumbnail-info').show();
        
        // Create a progress timer to update status
        let seconds = 0;
        const progressTimer = setInterval(function() {
            seconds++;
            updateGenerationStatus(seconds);
        }, 1000);
        
        function updateGenerationStatus(elapsed) {
            let status = "Thumbnail Generation in Progress";
            if (elapsed > 10) {
                status = "Still working on it...";
            }
            if (elapsed > 30) {
                status = "Almost there...";
            }
            if (elapsed > 60) {
                status = "This is taking longer than expected...";
            }
            $('.generation-status').text(status);
        }
        
        // Send request
        $.ajax({
            url: `/admin/document/${docId}/generate-thumbnail`,
            type: 'POST',
            success: function(response) {
                // Clear the timer
                clearInterval(progressTimer);
                
                if (response.success) {
                    // Update status
                    $('.generation-status').text("Thumbnail Successfully Generated!");
                    $('.thumbnail-info').removeClass('alert-info').addClass('alert-success');
                    $('.progress-container').html('<span class="material-symbols-outlined text-success" style="font-size: 2rem;">check_circle</span>');
                    
                    // Show success message
                    toastr.success(response.message);
                    
                    // Refresh the page after a short delay to show the new thumbnail
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    // Hide the info alert
                    $('.thumbnail-info').hide();
                    
                    // Show error message
                    toastr.error(response.message || 'Failed to generate thumbnail');
                    
                    // Reset button
                    btn.prop('disabled', false).text(originalText);
                }
            },
            error: function(xhr) {
                // Clear the timer
                clearInterval(progressTimer);
                
                // Hide the info alert
                $('.thumbnail-info').hide();
                
                // Show error message
                let errorMessage = 'Failed to generate thumbnail';
                try {
                    errorMessage = JSON.parse(xhr.responseText).message || errorMessage;
                } catch (e) {}
                
                toastr.error(errorMessage);
                
                // Reset button
                btn.prop('disabled', false).text(originalText);
            }
        });
    });
    
    // Reset thumbnail
    $('#btn-reset-thumbnail').click(function() {
        // Show loading indicator
        const btn = $(this);
        const originalText = btn.text();
        btn.prop('disabled', true).html('<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Resetting...');
        
        // Show the info alert
        $('.thumbnail-info').show();
        $('.generation-status').text("Resetting thumbnail...");
        
        // Create a progress timer to update status
        let seconds = 0;
        const progressTimer = setInterval(function() {
            seconds++;
            let status = "Resetting thumbnail...";
            if (seconds > 5) {
                status = "Generating default thumbnail...";
            }
            if (seconds > 15) {
                status = "Almost done...";
            }
            $('.generation-status').text(status);
        }, 1000);
        
        // Send request
        $.ajax({
            url: `/admin/document/${docId}/reset-thumbnail`,
            type: 'POST',
            success: function(response) {
                // Clear the timer
                clearInterval(progressTimer);
                
                if (response.success) {
                    // Update status
                    $('.generation-status').text("Thumbnail Successfully Reset!");
                    $('.thumbnail-info').removeClass('alert-info').addClass('alert-success');
                    $('.progress-container').html('<span class="material-symbols-outlined text-success" style="font-size: 2rem;">check_circle</span>');
                    
                    // Show success message
                    toastr.success(response.message);
                    
                    // Refresh the page after a short delay to show the new thumbnail
                    setTimeout(function() {
                        location.reload();
                    }, 1500);
                } else {
                    // Hide the info alert
                    $('.thumbnail-info').hide();
                    
                    // Show error message
                    toastr.error(response.message || 'Failed to reset thumbnail');
                    
                    // Reset button
                    btn.prop('disabled', false).text(originalText);
                }
            },
            error: function(xhr) {
                // Clear the timer
                clearInterval(progressTimer);
                
                // Hide the info alert
                $('.thumbnail-info').hide();
                
                // Show error message
                let errorMessage = 'Failed to reset thumbnail';
                try {
                    errorMessage = JSON.parse(xhr.responseText).message || errorMessage;
                } catch (e) {}
                
                toastr.error(errorMessage);
                
                // Reset button
                btn.prop('disabled', false).text(originalText);
            }
        });
    });
});