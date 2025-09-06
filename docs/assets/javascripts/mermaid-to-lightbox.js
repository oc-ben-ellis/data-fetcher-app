/**
 * Mermaid Popup Handler
 * Makes Mermaid diagrams clickable and opens them in popup windows
 */

// Multiple initialization strategies to ensure the script runs
function initializeMermaidPopup() {
    console.log('Mermaid Popup: Initializing...');

    // Wait for Mermaid to be loaded and initialized
    function waitForMermaid() {
        return new Promise((resolve) => {
            if (window.mermaid) {
                console.log('Mermaid Popup: Mermaid found immediately');
                resolve();
            } else {
                console.log('Mermaid Popup: Waiting for Mermaid to load...');
                const checkMermaid = setInterval(() => {
                    if (window.mermaid) {
                        console.log('Mermaid Popup: Mermaid loaded!');
                        clearInterval(checkMermaid);
                        resolve();
                    }
                }, 100);
            }
        });
    }

    async function makeMermaidClickable() {
        await waitForMermaid();

        // Wait for mermaid2 plugin to finish processing
        console.log('Mermaid Popup: Waiting for mermaid2 plugin to finish...');
        await new Promise(resolve => setTimeout(resolve, 2000));

        const mermaidElements = document.querySelectorAll('.mermaid');
        console.log(`Mermaid Popup: Found ${mermaidElements.length} Mermaid diagrams`);

        mermaidElements.forEach((element, index) => {
            try {
                // Skip if already processed
                if (element.closest('.mermaid-clickable')) {
                    console.log(`Mermaid Popup: Diagram ${index + 1} already processed, skipping`);
                    return;
                }

                // Get the Mermaid code
                const codeElement = element.querySelector('code');
                if (!codeElement) {
                    console.log(`Mermaid Popup: No code element found in diagram ${index + 1}`);
                    return;
                }

                const mermaidCode = codeElement.textContent;
                console.log(`Mermaid Popup: Processing diagram ${index + 1} with code:`, mermaidCode.substring(0, 100) + '...');

                // Create a clickable wrapper
                const wrapper = document.createElement('div');
                wrapper.style.cssText = `
                    position: relative;
                    cursor: pointer;
                    border: 2px solid transparent;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                `;

                // Add hover effect
                wrapper.addEventListener('mouseenter', function () {
                    this.style.borderColor = '#9f1f34';
                    this.style.backgroundColor = 'rgba(159, 31, 52, 0.05)';
                });

                wrapper.addEventListener('mouseleave', function () {
                    this.style.borderColor = 'transparent';
                    this.style.backgroundColor = 'transparent';
                });

                // Add click handler
                wrapper.addEventListener('click', function () {
                    openMermaidPopup(mermaidCode);
                });

                // Add click indicator
                const clickIndicator = document.createElement('div');
                clickIndicator.style.cssText = `
                    position: absolute;
                    top: 8px;
                    right: 8px;
                    background: rgba(159, 31, 52, 0.9);
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: bold;
                    opacity: 0;
                    transition: opacity 0.3s ease;
                    pointer-events: none;
                    z-index: 10;
                `;
                clickIndicator.textContent = 'Click to expand';

                // Show indicator on hover
                wrapper.addEventListener('mouseenter', function () {
                    clickIndicator.style.opacity = '1';
                });

                wrapper.addEventListener('mouseleave', function () {
                    clickIndicator.style.opacity = '0';
                });

                // Wrap the original element
                element.parentNode.insertBefore(wrapper, element);
                wrapper.appendChild(element);
                wrapper.appendChild(clickIndicator);

                console.log(`Mermaid Popup: Made diagram ${index + 1} clickable`);

            } catch (error) {
                console.error(`Mermaid Popup: Error processing diagram ${index + 1}:`, error);
            }
        });

        console.log('Mermaid Popup: Initialization complete');
    }

    function openMermaidPopup(mermaidCode) {
        // Create popup window
        const popup = window.open('', 'mermaidPopup', 'width=1000,height=700,scrollbars=yes,resizable=yes,menubar=no,toolbar=no');

        if (!popup) {
            alert('Popup blocked. Please allow popups for this site.');
            return;
        }

        // Create HTML content for popup
        const htmlContent = `
        <!DOCTYPE html>
        <html>
        <head>
            <title>Mermaid Diagram - Data Pipeline Documentation</title>
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
            <style>
                body {
                    margin: 0;
                    padding: 20px;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #f8f9fa;
                }
                .container {
                    max-width: 100%;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                .header {
                    background: #9f1f34;
                    color: white;
                    padding: 15px 20px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .header h1 {
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                }
                .controls {
                    display: flex;
                    gap: 10px;
                }
                .controls button {
                    padding: 8px 16px;
                    background: rgba(255,255,255,0.2);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: background 0.2s ease;
                }
                .controls button:hover {
                    background: rgba(255,255,255,0.3);
                }
                .content {
                    padding: 20px;
                    text-align: center;
                }
                .mermaid {
                    display: inline-block;
                }
                .loading {
                    color: #6c757d;
                    font-style: italic;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Mermaid Diagram</h1>
                    <div class="controls">
                        <button onclick="downloadSVG()">Download SVG</button>
                        <button onclick="window.print()">Print</button>
                        <button onclick="window.close()">Close</button>
                    </div>
                </div>
                <div class="content">
                    <div class="loading">Loading diagram...</div>
                    <div class="mermaid" style="display: none;">${mermaidCode}</div>
                </div>
            </div>

            <script>
                // Initialize Mermaid with OpenCorporates theme
                mermaid.initialize({
                    theme: 'default',
                    themeVariables: {
                        primaryColor: '#9f1f34',
                        primaryTextColor: '#2c3e50',
                        primaryBorderColor: '#9f1f34',
                        lineColor: '#6c757d',
                        secondaryColor: '#f8f9fa',
                        tertiaryColor: '#ffffff'
                    },
                    startOnLoad: true
                });

                // Hide loading message and show diagram when ready
                document.addEventListener('DOMContentLoaded', function() {
                    setTimeout(() => {
                        document.querySelector('.loading').style.display = 'none';
                        document.querySelector('.mermaid').style.display = 'inline-block';
                    }, 500);
                });

                function downloadSVG() {
                    const svg = document.querySelector('svg');
                    if (svg) {
                        const svgData = new XMLSerializer().serializeToString(svg);
                        const svgBlob = new Blob([svgData], {type: 'image/svg+xml;charset=utf-8'});
                        const svgUrl = URL.createObjectURL(svgBlob);
                        const downloadLink = document.createElement('a');
                        downloadLink.href = svgUrl;
                        downloadLink.download = 'mermaid-diagram.svg';
                        document.body.appendChild(downloadLink);
                        downloadLink.click();
                        document.body.removeChild(downloadLink);
                        URL.revokeObjectURL(svgUrl);
                    } else {
                        alert('Diagram not ready yet. Please wait a moment and try again.');
                    }
                }
            </script>
        </body>
        </html>
        `;

        popup.document.write(htmlContent);
        popup.document.close();

        // Focus the popup window
        popup.focus();
    }

    // Start the initialization process with retry
    makeMermaidClickable().catch(() => {
        console.log('Mermaid Popup: Initial attempt failed, retrying in 2 seconds...');
        setTimeout(() => {
            makeMermaidClickable();
        }, 2000);
    });
}

// Multiple initialization strategies
console.log('Mermaid Popup: Script loaded');

// Strategy 1: DOMContentLoaded
document.addEventListener('DOMContentLoaded', initializeMermaidPopup);

// Strategy 2: If DOM is already loaded
if (document.readyState === 'loading') {
    console.log('Mermaid Popup: DOM still loading, waiting for DOMContentLoaded');
} else {
    console.log('Mermaid Popup: DOM already loaded, initializing immediately');
    setTimeout(initializeMermaidPopup, 100);
}

// Strategy 3: Window load event as fallback
window.addEventListener('load', () => {
    console.log('Mermaid Popup: Window loaded, checking if initialization is needed');
    setTimeout(() => {
        const mermaidElements = document.querySelectorAll('.mermaid');
        if (mermaidElements.length > 0 && !document.querySelector('.mermaid-clickable')) {
            console.log('Mermaid Popup: Fallback initialization triggered');
            initializeMermaidPopup();
        }
    }, 1000);
});
