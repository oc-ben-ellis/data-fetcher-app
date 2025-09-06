"""Custom MkDocs plugin for sidebar toggle functionality.

This plugin adds a toggle button to the Material theme that allows users
to show/hide the navigation and table of contents sidebars.
"""

from pathlib import Path
from typing import Any

from mkdocs.config import config_options
from mkdocs.plugins import BasePlugin


class SidebarTogglePlugin(BasePlugin[Any]):  # type: ignore[no-untyped-call]
    """Plugin to add sidebar toggle functionality to MkDocs Material theme."""

    config_scheme = (
        ('show_navigation_by_default', config_options.Type(bool, default=True)),
        ('show_toc_by_default', config_options.Type(bool, default=True)),
        ('toggle_button_position', config_options.Choice(['top-right', 'top-left', 'header'], default='top-right')),
        ('toggle_button_style', config_options.Choice(['floating', 'inline'], default='floating')),
    )

    def __init__(self) -> None:
        self.enabled = True

    def on_config(self, config: Any) -> Any:  # noqa: ANN401
        """Called after the config is loaded and validated."""
        return config

    def on_page_content(self, html: str, page: Any, config: Any, files: Any) -> str:  # noqa: ANN401, ARG002
        """Called after the page content is rendered."""
        return html

    def on_post_page(self, output: str, page: Any, config: Any) -> str:  # noqa: ANN401, ARG002
        """Called after the page is rendered but before it is written to disk."""
        return output

    def on_post_build(self, config: Any) -> None:  # noqa: ANN401
        """Called after the build is complete."""
        # Add the CSS and JavaScript files to the site
        self._add_css_file(config)
        self._add_js_file(config)

    def _add_css_file(self, config: Any) -> None:  # noqa: ANN401
        """Add the CSS file for the toggle button styling."""
        css_content = """
/* Sidebar Toggle Button Styles */
.sidebar-toggle-btn {
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
    font-size: 16px;
}

.sidebar-toggle-btn:hover {
    transform: scale(1.1);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}

.sidebar-toggle-btn:active {
    transform: scale(0.95);
}

/* Dark mode support */
[data-md-color-scheme="slate"] .sidebar-toggle-btn {
    background: var(--md-primary-fg-color, #fff);
    color: var(--md-primary-bg-color, #000);
}

/* Hide sidebars when toggled */
.sidebars-hidden .md-sidebar--primary,
.sidebars-hidden .md-sidebar--secondary {
    display: none !important;
}

.sidebars-hidden .md-content {
    margin-left: 0 !important;
    margin-right: 0 !important;
}

/* Responsive adjustments */
@media screen and (max-width: 76.1875em) {
    .sidebar-toggle-btn {
        top: 10px;
        right: 10px;
        width: 35px;
        height: 35px;
        font-size: 14px;
    }
}
"""

        css_path = Path(config['site_dir']) / 'assets' / 'stylesheets' / 'sidebar-toggle.css'
        css_path.parent.mkdir(parents=True, exist_ok=True)

        css_path.write_text(css_content, encoding='utf-8')

    def _add_js_file(self, config: Any) -> None:  # noqa: ANN401
        """Add the JavaScript file for the toggle button functionality."""
        js_content = """
/**
 * Sidebar Toggle Plugin
 * Adds functionality to toggle navigation and TOC sidebars
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Sidebar Toggle Plugin: Initializing...');

    // Create toggle button
    function createToggleButton() {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'sidebar-toggle-btn';
        toggleBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 6h18v2H3V6m0 5h18v2H3v-2m0 5h18v2H3v-2Z"/>
            </svg>
        `;
        toggleBtn.title = 'Toggle Sidebars (B)';
        toggleBtn.setAttribute('aria-label', 'Toggle sidebars');

        return toggleBtn;
    }

    // Toggle function
    function toggleSidebars() {
        const body = document.body;
        const isHidden = body.classList.contains('sidebars-hidden');

        if (isHidden) {
            // Show sidebars
            body.classList.remove('sidebars-hidden');
            console.log('Sidebar Toggle: Sidebars shown');
        } else {
            // Hide sidebars
            body.classList.add('sidebars-hidden');
            console.log('Sidebar Toggle: Sidebars hidden');
        }

        // Save state to localStorage
        localStorage.setItem('sidebars-hidden', !isHidden);
    }

    // Restore state from localStorage
    function restoreState() {
        const isHidden = localStorage.getItem('sidebars-hidden') === 'true';
        if (isHidden) {
            document.body.classList.add('sidebars-hidden');
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

    // Restore previous state
    restoreState();

    console.log('Sidebar Toggle Plugin: Ready! Press B or click the button to toggle sidebars.');
});
"""

        js_path = Path(config['site_dir']) / 'assets' / 'javascripts' / 'sidebar-toggle.js'
        js_path.parent.mkdir(parents=True, exist_ok=True)

        js_path.write_text(js_content, encoding='utf-8')

    def on_template_context(self, context: Any, *, template_name: str, config: Any) -> Any:  # noqa: ANN401, ARG002
        """Called before a template is rendered."""
        # Add the CSS and JS files to the template context
        if 'extra_css' not in context:
            context['extra_css'] = []
        if 'extra_javascript' not in context:
            context['extra_javascript'] = []

        context['extra_css'].append('assets/stylesheets/sidebar-toggle.css')
        context['extra_javascript'].append('assets/javascripts/sidebar-toggle.js')

        return context
