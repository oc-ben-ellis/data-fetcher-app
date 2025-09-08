/**
 * Simple Sidebar Toggle
 * A direct implementation for toggling sidebars without external plugins
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Simple Sidebar Toggle: Initializing...');

    // Create toggle button
    function createToggleButton() {
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'sidebar-toggle-btn';
        toggleBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2Z"/>
            </svg>
        `;
        toggleBtn.title = 'Toggle Sidebars (B)';
        toggleBtn.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: var(--md-primary-fg-color, #000);
            color: var(--md-primary-bg-color, #fff);
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            transition: all 0.2s ease;
        `;

        // Add hover effect
        toggleBtn.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.1)';
            this.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3)';
        });

        toggleBtn.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1)';
            this.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
        });

        return toggleBtn;
    }

    // Toggle function
    function toggleSidebars() {
        const navSidebar = document.querySelector('.md-sidebar--primary');
        const tocSidebar = document.querySelector('.md-sidebar--secondary');
        const mainContent = document.querySelector('.md-content');

        if (navSidebar && tocSidebar) {
            const isHidden = navSidebar.style.display === 'none';

            if (isHidden) {
                // Show sidebars
                navSidebar.style.display = '';
                tocSidebar.style.display = '';
                if (mainContent) {
                    mainContent.style.marginLeft = '';
                    mainContent.style.marginRight = '';
                }
                console.log('Simple Sidebar Toggle: Sidebars shown');
            } else {
                // Hide sidebars
                navSidebar.style.display = 'none';
                tocSidebar.style.display = 'none';
                if (mainContent) {
                    mainContent.style.marginLeft = '0';
                    mainContent.style.marginRight = '0';
                }
                console.log('Simple Sidebar Toggle: Sidebars hidden');
            }
        }
    }

    // Add button to page
    const toggleBtn = createToggleButton();
    document.body.appendChild(toggleBtn);

    // Add click handler
    toggleBtn.addEventListener('click', toggleSidebars);

    // Add keyboard shortcut (B key)
    document.addEventListener('keydown', function(e) {
        if (e.key === 'b' || e.key === 'B') {
            if (!e.ctrlKey && !e.altKey && !e.metaKey) {
                // Only trigger if not typing in an input field
                if (!['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
                    e.preventDefault();
                    toggleSidebars();
                }
            }
        }
    });

    console.log('Simple Sidebar Toggle: Ready! Press B or click the button to toggle sidebars.');
});
