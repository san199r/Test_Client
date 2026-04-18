/**
 * Crown Ridge Land Holdings - Frontend Logic
 * Updated for Long-Scrolling Navigation
 */

document.addEventListener('DOMContentLoaded', () => {
    // Mobile Menu Logic
    const mobileToggle = document.querySelector('.mobile-toggle');
    const navLinksList = document.querySelector('.nav-links');
    
    if (mobileToggle) {
        mobileToggle.addEventListener('click', () => {
            mobileToggle.classList.toggle('active');
            navLinksList.classList.toggle('active');
        });
    }

    // Smooth Scroll for Nav Links
    const navLinks = document.querySelectorAll('.nav-links a, .service-suite, .footer-nav a, #home-link');
    
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            // Close mobile menu if open
            if (mobileToggle && mobileToggle.classList.contains('active')) {
                mobileToggle.classList.remove('active');
                navLinksList.classList.remove('active');
            }

            let targetId = '';
            
            // Handle different types of targets
            if (link.classList.contains('service-suite')) {
                // Get target from the onclick attribute I had before
                const onclickStr = link.getAttribute('onclick');
                if (onclickStr) targetId = onclickStr.match(/'([^']+)'/)[1];
            } else {
                const href = link.getAttribute('href');
                if (href && href.startsWith('#')) targetId = href.replace('#', '');
                if (link.id === 'home-link') targetId = 'home';
            }

            if (targetId) {
                e.preventDefault();
                scrollToSection(targetId);
                history.pushState(null, null, `#${targetId}`);
            }
        });
    });

    // Form Submissions
    setupForm('seller-form', '/api/seller', 'Inquiry Received. Our acquisitions team will contact you within 48 hours.');
    setupForm('investor-form', '/api/investor', 'Application Received. You will receive an invitation to the portal shortly.');
});

/**
 * Smooth scroll to target section
 */
function scrollToSection(id) {
    const target = document.getElementById(id);
    if (target) {
        target.scrollIntoView({
            behavior: "smooth"
        });

        // Update active nav state
        updateActiveNav(id);
    }
}

/**
 * Handle form submissions and API communication
 */
function setupForm(formId, apiEndpoint, successMessage) {
    const form = document.getElementById(formId);
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button');
        const originalText = btn.innerText;
        
        // Disable UI
        btn.disabled = true;
        btn.innerText = 'PROCESSING...';

        // Collect Form Data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Convert acreage to number if it exists
        if (data.acreage) data.acreage = parseFloat(data.acreage);

        try {
            const response = await fetch(apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            if (!response.ok) throw new Error('Network response was not ok');

            const result = await response.json();

            // Success Visual
            form.innerHTML = `
                <div class="success-box text-center">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                    <h3 class="serif">Submission Successful</h3>
                    <p style="font-size: 0.9rem;">${successMessage}</p>
                </div>
            `;
        } catch (error) {
            console.error('Submission error:', error);
            btn.disabled = false;
            btn.innerText = 'ERROR - TRY AGAIN';
            
            // Temporary error toast or alert
            const errEl = document.createElement('p');
            errEl.style.color = 'red';
            errEl.style.fontSize = '0.7rem';
            errEl.style.marginTop = '10px';
            errEl.innerText = 'Could not connect to the server. Please try again later.';
            form.appendChild(errEl);
            setTimeout(() => errEl.remove(), 4000);
        }
    });
}

function updateActiveNav(id) {
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === `#${id}`) link.classList.add('active');
    });
}

// Global exposure for any existing onclicks
window.showSection = scrollToSection;
