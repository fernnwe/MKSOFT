/* ============================================
   Material Design 3 (Material You) - JavaScript
   Components: Drawer, Avatar dropdown, Dark Mode,
   Ripple Effect, Dialog, Snackbar, Scroll effects
   ============================================ */

(function () {
    'use strict';

    // --- Dark Mode ---
    const THEME_KEY = 'md3-theme';

    function getPreferredTheme() {
        try { var stored = localStorage.getItem(THEME_KEY); if (stored) return stored; } catch(e) {}
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }

    function setTheme(theme) {
        document.documentElement.setAttribute('data-md3-theme', theme);
        try { localStorage.setItem(THEME_KEY, theme); } catch(e) {}
        // Update toggle button icon if it exists
        const btn = document.querySelector('.md3-theme-toggle .material-symbols-outlined');
        if (btn) {
            btn.textContent = theme === 'dark' ? 'light_mode' : 'dark_mode';
        }
    }

    function toggleTheme() {
        const current = document.documentElement.getAttribute('data-md3-theme') || 'light';
        setTheme(current === 'dark' ? 'light' : 'dark');
    }

    // Initialize theme
    setTheme(getPreferredTheme());

    // Listen for system preference changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
        if (!localStorage.getItem(THEME_KEY)) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });

    // Expose for inline usage
    window.md3ToggleTheme = toggleTheme;

    // --- Ripple Effect ---
    var touchFired = false;

    function createRipple(e) {
        const el = e.currentTarget;
        const rect = el.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const cx = e.clientX != null ? e.clientX : (e.touches?.[0]?.clientX ?? rect.left + rect.width / 2);
        const cy = e.clientY != null ? e.clientY : (e.touches?.[0]?.clientY ?? rect.top + rect.height / 2);
        const x = cx - rect.left - size / 2;
        const y = cy - rect.top - size / 2;

        const ripple = document.createElement('span');
        ripple.className = 'md3-ripple';
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = x + 'px';
        ripple.style.top = y + 'px';

        el.appendChild(ripple);
        ripple.addEventListener('animationend', function () {
            ripple.remove();
        });
    }

    function initRipples(container) {
        const selectors = '.md3-btn, .md3-menu-btn, .md3-nav-item, .md3-avatar-dropdown-item, .md3-chip, .md3-nav-rail-item';
        const els = (container || document).querySelectorAll(selectors);
        els.forEach(function (el) {
            if (!el.classList.contains('md3-ripple-ready')) {
                el.classList.add('md3-ripple-ready');
                if (getComputedStyle(el).position === 'static') {
                    el.style.position = 'relative';
                }
                el.style.overflow = 'hidden';
                el.addEventListener('touchstart', function (e) {
                    touchFired = true;
                    createRipple(e);
                }, { passive: true });
                el.addEventListener('mousedown', function (e) {
                    if (touchFired) { touchFired = false; return; }
                    createRipple(e);
                });
            }
        });
    }

    window.md3InitRipples = initRipples;

    // --- Navigation Drawer ---
    function initDrawer() {
        const menuBtn = document.getElementById('menuBtn');
        const navDrawer = document.getElementById('navDrawer');
        const navOverlay = document.getElementById('navOverlay');
        if (!menuBtn || !navDrawer || !navOverlay) return;

        menuBtn.addEventListener('click', function () {
            navDrawer.classList.toggle('open');
            navOverlay.classList.toggle('visible');
        });

        navOverlay.addEventListener('click', function () {
            navDrawer.classList.remove('open');
            navOverlay.classList.remove('visible');
        });

        // Close on Escape key
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && navDrawer.classList.contains('open')) {
                navDrawer.classList.remove('open');
                navOverlay.classList.remove('visible');
            }
        });

        // Auto-close on desktop resize
        function handleResize() {
            if (window.innerWidth >= 1024) {
                navDrawer.classList.remove('open');
                navOverlay.classList.remove('visible');
            }
        }
        window.addEventListener('resize', handleResize);
        handleResize();
    }

    // --- Avatar Dropdown ---
    function initAvatarDropdown() {
        const avatarBtn = document.getElementById('avatarBtn');
        const avatarDropdown = document.getElementById('avatarDropdown');
        if (!avatarBtn || !avatarDropdown) return;

        avatarBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            avatarDropdown.classList.toggle('open');
        });

        document.addEventListener('click', function (e) {
            if (!avatarDropdown.contains(e.target) && e.target !== avatarBtn) {
                avatarDropdown.classList.remove('open');
            }
        });
    }

    // --- Scroll Effect on Top App Bar ---
    function initScrollEffect() {
        const topAppBar = document.getElementById('topAppBar');
        if (!topAppBar) return;

        window.addEventListener('scroll', function () {
            if (window.scrollY > 8) {
                topAppBar.classList.add('scrolled');
            } else {
                topAppBar.classList.remove('scrolled');
            }
        }, { passive: true });
    }

    // --- Snackbar ---
    window.md3ShowSnackbar = function (message, duration) {
        var existing = document.querySelector('.md3-snackbar');
        if (existing) existing.remove();

        var snackbar = document.createElement('div');
        snackbar.className = 'md3-snackbar';
        snackbar.textContent = message;
        document.body.appendChild(snackbar);

        requestAnimationFrame(function () {
            snackbar.classList.add('show');
        });

        setTimeout(function () {
            snackbar.classList.remove('show');
            setTimeout(function () { snackbar.remove(); }, 300);
        }, duration || 3000);
    };

    // --- Dialog ---
    function escapeHtml(str) {
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    window.md3ShowDialog = function (opts) {
        opts = opts || {};
        var overlay = document.createElement('div');
        overlay.className = 'md3-dialog-overlay';
        overlay.innerHTML =
            '<div class="md3-dialog">' +
            (opts.title ? '<div class="md3-dialog-header"><h2 class="md3-dialog-title">' + escapeHtml(opts.title) + '</h2></div>' : '') +
            (opts.content ? '<div class="md3-dialog-content">' + escapeHtml(opts.content) + '</div>' : '') +
            '<div class="md3-dialog-actions">' +
            (opts.cancelText ? '<button class="md3-btn md3-btn-outlined md3-dialog-cancel">' + escapeHtml(opts.cancelText) + '</button>' : '') +
            (opts.confirmText ? '<button class="md3-btn md3-btn-filled md3-dialog-confirm">' + escapeHtml(opts.confirmText) + '</button>' : '') +
            '</div></div>';

        document.body.appendChild(overlay);

        requestAnimationFrame(function () {
            overlay.classList.add('open');
            initRipples(overlay);
        });

        return new Promise(function (resolve) {
            var cancelBtn = overlay.querySelector('.md3-dialog-cancel');
            var confirmBtn = overlay.querySelector('.md3-dialog-confirm');

            function close(result) {
                overlay.classList.remove('open');
                setTimeout(function () { overlay.remove(); }, 200);
                if (opts.onClose) opts.onClose(result);
                resolve(result);
            }

            if (cancelBtn) {
                cancelBtn.addEventListener('click', function () { close(false); });
            }
            if (confirmBtn) {
                confirmBtn.addEventListener('click', function () { close(true); });
            }
            overlay.addEventListener('click', function (e) {
                if (e.target === overlay) close(false);
            });
        });
    };

    // --- WebSocket helper ---
    window.md3WsBase = (function () {
        var protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return protocol + '//' + window.location.host;
    })();

    // --- Init on DOM ready ---
    document.addEventListener('DOMContentLoaded', function () {
        initDrawer();
        initAvatarDropdown();
        initScrollEffect();
        initRipples();
    });

})();
