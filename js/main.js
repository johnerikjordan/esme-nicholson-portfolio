/**
 * Esme Nicholson Portfolio - Main JavaScript
 *
 * Features:
 * - Smooth scrolling for navigation links
 * - Sticky nav shadow on scroll
 * - Active section highlighting
 * - Mobile navigation toggle
 * - Load article images from JSON data
 */

(function() {
    'use strict';

    // DOM Elements
    const nav = document.getElementById('nav');
    const hamburger = document.querySelector('.nav__hamburger');
    const mobileNav = document.getElementById('mobileNav');
    const navLinks = document.querySelectorAll('.nav__link');
    const mobileLinks = document.querySelectorAll('.nav__mobile-link');
    const sections = document.querySelectorAll('section[id]');

    /**
     * Initialize all functionality when DOM is ready
     */
    function init() {
        setupSmoothScrolling();
        setupNavShadow();
        setupMobileNav();
        setupActiveSection();
        loadArticleImages();
    }

    /**
     * Smooth scrolling for anchor links
     */
    function setupSmoothScrolling() {
        const allNavLinks = [...navLinks, ...mobileLinks];

        allNavLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                const href = this.getAttribute('href');

                if (href.startsWith('#')) {
                    e.preventDefault();
                    const target = document.querySelector(href);

                    if (target) {
                        // Close mobile nav if open
                        closeMobileNav();

                        // Scroll to target
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });

        // Logo click scrolls to top
        const logo = document.querySelector('.nav__logo');
        if (logo) {
            logo.addEventListener('click', function(e) {
                e.preventDefault();
                window.scrollTo({
                    top: 0,
                    behavior: 'smooth'
                });
            });
        }
    }

    /**
     * Add shadow to nav when scrolled
     */
    function setupNavShadow() {
        const scrollThreshold = 50;

        function updateNavShadow() {
            if (window.scrollY > scrollThreshold) {
                nav.classList.add('scrolled');
            } else {
                nav.classList.remove('scrolled');
            }
        }

        // Initial check
        updateNavShadow();

        // Listen for scroll events with throttling
        let ticking = false;
        window.addEventListener('scroll', function() {
            if (!ticking) {
                window.requestAnimationFrame(function() {
                    updateNavShadow();
                    ticking = false;
                });
                ticking = true;
            }
        });
    }

    /**
     * Mobile navigation toggle
     */
    function setupMobileNav() {
        if (!hamburger || !mobileNav) return;

        hamburger.addEventListener('click', function() {
            toggleMobileNav();
        });

        // Close mobile nav when clicking outside
        mobileNav.addEventListener('click', function(e) {
            if (e.target === mobileNav) {
                closeMobileNav();
            }
        });

        // Close mobile nav on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && mobileNav.classList.contains('active')) {
                closeMobileNav();
            }
        });
    }

    function toggleMobileNav() {
        hamburger.classList.toggle('active');
        mobileNav.classList.toggle('active');
        document.body.style.overflow = mobileNav.classList.contains('active') ? 'hidden' : '';
    }

    function closeMobileNav() {
        hamburger.classList.remove('active');
        mobileNav.classList.remove('active');
        document.body.style.overflow = '';
    }

    /**
     * Highlight active section in navigation
     */
    function setupActiveSection() {
        const observerOptions = {
            root: null,
            rootMargin: '-20% 0px -60% 0px',
            threshold: 0
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const id = entry.target.getAttribute('id');
                    updateActiveLink(id);
                }
            });
        }, observerOptions);

        sections.forEach(section => {
            observer.observe(section);
        });
    }

    function updateActiveLink(activeId) {
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === `#${activeId}`) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });

        mobileLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href === `#${activeId}`) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    }

    /**
     * Load article images from JSON data
     */
    async function loadArticleImages() {
        try {
            const response = await fetch('data/articles.json');
            if (!response.ok) {
                console.log('Could not load articles.json');
                return;
            }

            const articles = await response.json();
            const cards = document.querySelectorAll('.card');

            cards.forEach((card, index) => {
                const article = articles[index];
                if (!article) return;

                // Update card with image if available
                if (article.image) {
                    const imageContainer = card.querySelector('.card__image');
                    const placeholder = card.querySelector('.card__image-placeholder');

                    if (imageContainer && placeholder) {
                        const img = document.createElement('img');
                        img.src = article.image;
                        img.alt = article.title;
                        img.loading = 'lazy';

                        img.onload = function() {
                            placeholder.style.display = 'none';
                            imageContainer.appendChild(img);
                        };

                        img.onerror = function() {
                            // Keep placeholder on error
                            console.log('Failed to load image for:', article.title);
                        };
                    }
                }
            });
        } catch (error) {
            console.log('Error loading article data:', error);
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
