// app.js - Global Logic and UI Injection
window.API_BASE = window.location.protocol === 'file:' ? 'http://localhost:5000' : '';

const App = {
  // Setup common UI elements (Navbar & Footer)
  init() {
    this.injectNavbar();
    this.injectFooter();
    this.checkAuthState();
  },

  injectNavbar() {
    const navbarHTML = `
      <header class="navbar">
        <div class="container">
          <a href="index.html" class="nav-brand">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            Complain 24
          </a>
          <nav class="nav-links" style="display: flex; align-items: center; gap: 1rem;">
            <!-- Google Translate Widget Container -->
            <div id="google_translate_element" style="transform: scale(0.85); transform-origin: center; display: inline-block;"></div>
            
            <a href="index.html" class="nav-link">Home</a>
            <a href="submit-complaint.html" class="nav-link">Submit Complaint</a>
            <a href="track-complaint.html" class="nav-link">Track Status</a>
            <a href="emergency.html" class="nav-link" style="color: var(--accent-alert); font-weight: 600;">Emergency</a>
            
            <!-- Theme Toggle Button -->
            <button id="themeToggleBtn" onclick="App.toggleTheme()" class="btn btn-outline" style="padding: 0.3rem 0.6rem; font-size: 1.1rem; border-color: transparent;">🌓</button>
            
            <div id="auth-links">
              <!-- Injected by checkAuthState -->
            </div>
          </nav>
        </div>
      </header>
    `;
    document.body.insertAdjacentHTML('afterbegin', navbarHTML);
  },

  injectFooter() {
    const footerHTML = `
      <footer class="footer">
        <div class="container">
          <div class="footer-grid">
            <div class="footer-col">
              <h4 class="nav-brand mb-4">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                Complain 24
              </h4>
              <p class="text-sm">Providing efficient, trustworthy, and accessible civic services to all citizens.</p>
            </div>
            <div class="footer-col">
              <h4>Quick Links</h4>
              <ul class="footer-links">
                <li><a href="submit-complaint.html">Submit Complaint</a></li>
                <li><a href="track-complaint.html">Track Complaint</a></li>
                <li><a href="notices.html">Public Notices</a></li>
                <li><a href="feedback.html">Give Feedback</a></li>
              </ul>
            </div>
            <div class="footer-col">
              <h4>Help & Support</h4>
              <ul class="footer-links">
                <li><a href="emergency.html" style="color: var(--accent-alert);">Emergency Helplines</a></li>
                <li><a href="contacts.html">Direct Department Contacts</a></li>
                <li><a href="#">FAQs</a></li>
                <li><a href="#">Terms of Service</a></li>
              </ul>
            </div>
          </div>
          <div class="footer-bottom">
            &copy; 2026 Complain 24. All rights reserved.
          </div>
        </div>
      </footer>
    `;
    document.body.insertAdjacentHTML('beforeend', footerHTML);
  },

  checkAuthState() {
    const authLinksContainer = document.getElementById('auth-links');
    if (!authLinksContainer) return;

    // Simulate auth check via localStorage
    const user = JSON.parse(localStorage.getItem('citizen_user'));
    
    if (user) {
      let dashboardLink = '';
      if (user.role === 'officer') {
        dashboardLink = '<a href="officer-dashboard.html" class="nav-link font-semibold">Dashboard</a>';
      } else if (user.role === 'supervisor') {
        dashboardLink = '<a href="supervisor-dashboard.html" class="nav-link font-semibold">Dashboard</a>';
      } else if (user.role === 'admin') {
        dashboardLink = '<a href="admin-dashboard.html" class="nav-link font-semibold">Dashboard</a>';
      } else {
        dashboardLink = '<a href="my-complaints.html" class="nav-link font-semibold" style="color: var(--primary-color);">My Complaints</a>';
      }

      authLinksContainer.innerHTML = `
        ${dashboardLink}
        <a href="#" class="nav-link" onclick="App.logout()">Logout (${user.name})</a>
      `;
    } else {
      authLinksContainer.innerHTML = `
        <a href="login.html" class="btn btn-outline" style="padding: 0.4rem 1rem;">Login</a>
        <a href="register.html" class="btn btn-primary" style="padding: 0.4rem 1rem;">Sign Up</a>
      `;
    }
  },

  logout() {
    localStorage.removeItem('citizen_user');
    window.location.href = 'index.html';
  },

  // Utility function for setting mock data
  setupMockData() {
    if (!localStorage.getItem('complaints')) {
      const mockComplaints = [
        {
          id: 'CMP-1001',
          title: 'Pothole on Main Street',
          category: 'Roads',
          status: 'Pending',
          priority: 'Normal',
          date: new Date().toISOString(),
          department: 'Public Works'
        },
        {
          id: 'CMP-1002',
          title: 'Streetlight not working',
          category: 'Electricity',
          status: 'In Progress',
          priority: 'Urgent',
          date: new Date(Date.now() - 86400000).toISOString(),
          department: 'Electrical Board'
        }
      ];
      localStorage.setItem('complaints', JSON.stringify(mockComplaints));
    }
  },

  toggleTheme() {
    const isLight = document.documentElement.classList.toggle('light-theme');
    localStorage.setItem('theme', isLight ? 'light' : 'dark');
    document.getElementById('themeToggleBtn').textContent = isLight ? '🌞' : '🌓';
  },
  
  loadTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'light') {
      document.documentElement.classList.add('light-theme');
      setTimeout(() => {
        const btn = document.getElementById('themeToggleBtn');
        if (btn) btn.textContent = '🌞';
      }, 100);
    }
  },
  
  injectGoogleTranslate() {
    const script = document.createElement('script');
    script.src = "//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit";
    document.body.appendChild(script);
    
    window.googleTranslateElementInit = function() {
      new google.translate.TranslateElement({pageLanguage: 'en'}, 'google_translate_element');
    };
  }
};

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
  App.setupMockData();
  App.init();
  App.loadTheme();
  App.injectGoogleTranslate();
});
