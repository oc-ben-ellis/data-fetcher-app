/**
 * Mermaid Modal Enhancement
 * Makes Mermaid diagrams clickable to open in a larger modal view
 */

document.addEventListener('DOMContentLoaded', function () {
    // Create modal HTML structure
    const modalHTML = `
        <div id="mermaid-modal" class="mermaid-modal-overlay" style="display: none;">
            <div class="mermaid-modal-content">
                <div class="mermaid-modal-header">
                    <h3 id="mermaid-modal-title">Diagram</h3>
                    <button class="mermaid-modal-close" id="mermaid-modal-close">&times;</button>
                </div>
                <div class="mermaid-modal-body">
                    <div id="mermaid-modal-diagram"></div>
                </div>
            </div>
        </div>
    `;

    // Add modal to page
    document.body.insertAdjacentHTML('beforeend', modalHTML);

    // Add CSS styles
    const modalCSS = `
        <style>
        .mermaid-modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.8);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
            box-sizing: border-box;
        }

        .mermaid-modal-content {
            background: white;
            border-radius: 8px;
            max-width: 95vw;
            max-height: 95vh;
            width: auto;
            height: auto;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .mermaid-modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            border-bottom: 1px solid #e0e0e0;
            background: #f8f9fa;
        }

        .mermaid-modal-header h3 {
            margin: 0;
            color: #333;
            font-size: 1.2em;
        }

        .mermaid-modal-close {
            background: none;
            border: none;
            font-size: 24px;
            cursor: pointer;
            color: #666;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: background-color 0.2s;
        }

        .mermaid-modal-close:hover {
            background-color: #e0e0e0;
            color: #333;
        }

        .mermaid-modal-body {
            padding: 20px;
            overflow: auto;
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .mermaid-modal-body svg {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
        }

        /* Make Mermaid diagrams clickable */
        .mermaid {
            cursor: pointer;
            transition: opacity 0.2s;
        }

        .mermaid:hover {
            opacity: 0.8;
        }

        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            .mermaid-modal-content {
                background: #1e1e1e;
                color: #ffffff;
            }

            .mermaid-modal-header {
                background: #2d2d2d;
                border-bottom-color: #404040;
            }

            .mermaid-modal-header h3 {
                color: #ffffff;
            }

            .mermaid-modal-close {
                color: #cccccc;
            }

            .mermaid-modal-close:hover {
                background-color: #404040;
                color: #ffffff;
            }
        }
        </style>
    `;

    // Add CSS to head
    document.head.insertAdjacentHTML('beforeend', modalCSS);

    // Get modal elements
    const modal = document.getElementById('mermaid-modal');
    const modalTitle = document.getElementById('mermaid-modal-title');
    const modalDiagram = document.getElementById('mermaid-modal-diagram');
    const closeBtn = document.getElementById('mermaid-modal-close');

    // Function to open modal
    function openMermaidModal(diagramElement, title) {
        // Get the original Mermaid content (the code block)
        const originalCode = diagramElement.querySelector('code');
        if (!originalCode) {
            console.error('No Mermaid code found in diagram element');
            return;
        }

        const mermaidCode = originalCode.textContent;

        // Set title
        modalTitle.textContent = title || 'Mermaid Diagram';

        // Clear and add new diagram with the original code
        modalDiagram.innerHTML = `<pre class="mermaid">${mermaidCode}</pre>`;

        // Show modal
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent background scrolling

        // Re-render Mermaid with the new content
        if (window.mermaid) {
            // Wait a bit for the modal to be visible, then initialize
            setTimeout(() => {
                mermaid.init(undefined, modalDiagram.querySelector('.mermaid'));
            }, 100);
        }
    }

    // Function to close modal
    function closeMermaidModal() {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Add click listeners to all Mermaid diagrams
    function addMermaidClickListeners() {
        const mermaidDiagrams = document.querySelectorAll('.mermaid');

        mermaidDiagrams.forEach((diagram, index) => {
            // Skip if already has click listener
            if (diagram.dataset.modalEnabled) return;

            diagram.dataset.modalEnabled = 'true';

            diagram.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();

                // Try to get a title from nearby heading or use default
                let title = 'Mermaid Diagram';
                const heading = diagram.closest('h1, h2, h3, h4, h5, h6') ||
                    diagram.previousElementSibling?.closest('h1, h2, h3, h4, h5, h6');
                if (heading) {
                    title = heading.textContent.trim();
                }

                openMermaidModal(diagram, title);
            });
        });
    }

    // Close modal events
    closeBtn.addEventListener('click', closeMermaidModal);

    modal.addEventListener('click', function (e) {
        if (e.target === modal) {
            closeMermaidModal();
        }
    });

    // Close on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            closeMermaidModal();
        }
    });

    // Initialize click listeners
    addMermaidClickListeners();

    // Re-initialize when new content is loaded (for dynamic content)
    const observer = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach(function (node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.classList && node.classList.contains('mermaid')) {
                            addMermaidClickListeners();
                        } else if (node.querySelectorAll) {
                            const newMermaidDiagrams = node.querySelectorAll('.mermaid');
                            if (newMermaidDiagrams.length > 0) {
                                addMermaidClickListeners();
                            }
                        }
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
