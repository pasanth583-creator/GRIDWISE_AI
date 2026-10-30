/**
 * GRIDWISE AI - Professional Enterprise UI Client Scripts
 * Sidebar toggle, mobile drawer, health polling, time filter switching.
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('⚡ GRIDWISE AI Professional Enterprise Client Initialized');

    // 1. Sidebar Collapse/Expand Toggle
    initSidebarToggle();

    // 2. Initialize Bootstrap Tooltips if available
    if (window.bootstrap && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    }

    // 3. Time Filter Toggle Handlers
    initTimeFilters();

    // 4. Check Backend Health
    checkSystemHealth();
});

/**
 * Initializes desktop sidebar collapse and mobile drawer toggle with overlay.
 */
function initSidebarToggle() {
    const sidebar = document.getElementById('gwSidebar');
    const mainWrapper = document.getElementById('gwMainWrapper');
    const toggleBtn = document.getElementById('gwSidebarToggle');
    const mobileToggleBtn = document.getElementById('gwMobileSidebarToggle');
    const overlay = document.getElementById('gwSidebarOverlay');

    if (!sidebar || !mainWrapper) return;

    // Restore desktop collapsed preference
    const isCollapsed = localStorage.getItem('gw_sidebar_collapsed') === 'true';
    if (isCollapsed && window.innerWidth >= 992) {
        sidebar.classList.add('collapsed');
        mainWrapper.classList.add('sidebar-collapsed');
    }

    // Toggle Desktop Collapse
    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            if (window.innerWidth >= 992) {
                sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('sidebar-collapsed');
                localStorage.setItem('gw_sidebar_collapsed', sidebar.classList.contains('collapsed'));
            } else {
                sidebar.classList.toggle('mobile-open');
                if (overlay) overlay.classList.toggle('active');
            }
        });
    }

    // Mobile Toggle Button
    if (mobileToggleBtn) {
        mobileToggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
            if (overlay) overlay.classList.toggle('active');
        });
    }

    // Click on overlay closes sidebar on mobile
    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
            overlay.classList.remove('active');
        });
    }
}

/**
 * Handles interactive pill switching on time filter groups.
 */
function initTimeFilters() {
    document.querySelectorAll('.gw-time-filters').forEach(group => {
        const buttons = group.querySelectorAll('.gw-time-filter-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                buttons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const filter = btn.getAttribute('data-filter');
                console.log(`Time filter switched to: ${filter}`);
                // Dispatches custom event if charts want to react
                document.dispatchEvent(new CustomEvent('gwTimeFilterChanged', { detail: { filter } }));
            });
        });
    });
}

/**
 * Pings the backend health endpoint and updates topbar status badge.
 */
async function checkSystemHealth() {
    const healthBadge = document.getElementById('gw-live-status-badge');
    if (!healthBadge) return;

    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'HEALTHY') {
                healthBadge.className = 'gw-badge gw-badge-green';
                healthBadge.innerHTML = '<span class="pulse-indicator"></span> System Online';
            } else {
                healthBadge.className = 'gw-badge gw-badge-amber';
                healthBadge.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Degraded';
            }
        } else {
            healthBadge.className = 'gw-badge gw-badge-amber';
            healthBadge.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Service Alert';
        }
    } catch (err) {
        healthBadge.className = 'gw-badge gw-badge-amber';
        healthBadge.innerHTML = '<i class="bi bi-wifi-off"></i> Offline';
    }
}
