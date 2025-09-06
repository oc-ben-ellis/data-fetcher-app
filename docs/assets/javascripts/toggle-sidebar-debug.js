/**
 * Toggle Sidebar Debug and Enhancement
 * Adds debugging and ensures the toggle button is visible
 */

document.addEventListener('DOMContentLoaded', function () {
    console.log('Toggle Sidebar Debug: DOM loaded');

    // Wait a bit for the toggle sidebar plugin to initialize
    setTimeout(() => {
        console.log('Toggle Sidebar Debug: Checking for toggle button...');

        // Check if the toggle button exists
        const toggleButton = document.querySelector('.mkdocs-toggle-sidebar-button');
        if (toggleButton) {
            console.log('Toggle Sidebar Debug: Toggle button found!', toggleButton);

            // Make sure it's visible
            toggleButton.style.display = 'inline-block';
            toggleButton.style.visibility = 'visible';
            toggleButton.style.opacity = '1';

            // Add a more prominent style
            toggleButton.style.backgroundColor = 'rgba(0, 0, 0, 0.1)';
            toggleButton.style.border = '1px solid rgba(0, 0, 0, 0.2)';
            toggleButton.style.borderRadius = '4px';
            toggleButton.style.padding = '4px';
            toggleButton.style.margin = '0 8px';

        } else {
            console.log('Toggle Sidebar Debug: Toggle button not found, trying to create one...');

            // Try to create the button manually
            const titleElement = document.querySelector('.md-header__title');
            if (titleElement) {
                console.log('Toggle Sidebar Debug: Found title element, creating button...');

                const toggleBtn = document.createElement('div');
                toggleBtn.className = 'mkdocs-toggle-sidebar-button';
                toggleBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2Z"></path></svg>`;
                toggleBtn.title = 'Toggle Navigation and Table of Contents';
                toggleBtn.style.cssText = `
                    display: inline-block !important;
                    width: 24px !important;
                    height: 24px !important;
                    margin: 0 8px !important;
                    padding: 4px !important;
                    cursor: pointer !important;
                    border-radius: 4px !important;
                    background-color: rgba(0, 0, 0, 0.1) !important;
                    border: 1px solid rgba(0, 0, 0, 0.2) !important;
                    transition: background-color 0.2s ease !important;
                    z-index: 1000 !important;
                `;

                // Add click handler
                toggleBtn.addEventListener('click', function () {
                    console.log('Toggle Sidebar Debug: Button clicked!');
                    if (window.MkdocsToggleSidebarPlugin) {
                        window.MkdocsToggleSidebarPlugin.toggleAllVisibility();
                    }
                });

                // Insert after title
                titleElement.parentNode.insertBefore(toggleBtn, titleElement.nextSibling);
                console.log('Toggle Sidebar Debug: Button created and inserted!');
            } else {
                console.log('Toggle Sidebar Debug: Title element not found');
            }
        }

        // Check if the plugin functions are available
        if (window.MkdocsToggleSidebarPlugin) {
            console.log('Toggle Sidebar Debug: Plugin functions available:', window.MkdocsToggleSidebarPlugin);
        } else {
            console.log('Toggle Sidebar Debug: Plugin functions not available');
        }

    }, 1000);
});
