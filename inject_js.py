import sys
sys.stdout.reconfigure(encoding='utf-8')

JS_CODE = """
<script>
/* ═══════════════════════════════════════════
   LANDING PAGE ENHANCEMENTS JS
═══════════════════════════════════════════ */

// ── Animated Counters (Intersection Observer) ──
(function() {
  function animateCounter(el) {
    var target = parseFloat(el.dataset.target);
    var suffix = el.dataset.suffix || '';
    var duration = 2000;
    var start = null;
    var isDecimal = target % 1 !== 0;
    // Format large numbers with abbreviations
    function formatVal(v) {
      if (suffix.includes('M+') && v >= 1000000) return (v/1000000).toFixed(1) + 'M+';
      if (suffix.includes('K+') && v >= 1000) return (v/1000).toFixed(0) + 'K+';
      if (isDecimal) return v.toFixed(1) + suffix;
      return Math.round(v) + suffix;
    }
    function step(ts) {
      if (!start) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var ease = 1 - Math.pow(1 - progress, 4);
      el.textContent = formatVal(target * ease);
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = formatVal(target);
    }
    requestAnimationFrame(step);
  }

  var counterObs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting && !e.target.dataset.counted) {
        e.target.dataset.counted = 'true';
        animateCounter(e.target);
      }
    });
  }, { threshold: 0.3 });

  function initCounters() {
    document.querySelectorAll('[data-target]').forEach(function(el) {
      counterObs.observe(el);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initCounters);
  } else {
    initCounters();
  }
})();

// ── Fade-in on scroll (Intersection Observer) ──
(function() {
  var fadeObs = new IntersectionObserver(function(entries) {
    entries.forEach(function(e) {
      if (e.isIntersecting) {
        e.target.style.animationPlayState = 'running';
        fadeObs.unobserve(e.target);
      }
    });
  }, { threshold: 0.15 });

  function initFade() {
    document.querySelectorAll('.fade-in-up, .feat-card-v2, .tech-card, .testi-card, .stat-card, .team-card, .hiw-step').forEach(function(el) {
      el.style.animationPlayState = 'paused';
      fadeObs.observe(el);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFade);
  } else {
    initFade();
  }
})();

// ── Hero Typing Effect ──
(function() {
  var phrases = [
    'Protecting Every Journey with AI',
    'Crime Prediction at 96.7% Accuracy',
    'Real-Time Traffic + Weather Analysis',
    'Personal Safety AI Guardian',
    'Smart City Digital Twin Platform'
  ];
  var idx = 0, charIdx = 0, deleting = false;

  function typeTick() {
    var el = document.querySelector('.hero-subtitle');
    if (!el) return;
    if (!el.dataset.originalText) el.dataset.originalText = el.textContent;
    
    var current = phrases[idx];
    if (!deleting) {
      el.textContent = current.slice(0, ++charIdx);
      if (charIdx === current.length) {
        deleting = true;
        setTimeout(typeTick, 2000);
        return;
      }
    } else {
      el.textContent = current.slice(0, --charIdx);
      if (charIdx === 0) {
        deleting = false;
        idx = (idx + 1) % phrases.length;
      }
    }
    setTimeout(typeTick, deleting ? 40 : 70);
  }

  // Only run typing on landing page hero
  document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('landing')) {
      setTimeout(typeTick, 1500);
    }
  });
})();

// ── Feature Cards Stagger ──
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    var cards = document.querySelectorAll('.feat-card-v2');
    cards.forEach(function(card, i) {
      card.style.animationDelay = (i * 0.05) + 's';
    });
  });
})();

// ── Twin Dashboard Live Counter ──
(function() {
  function updateTwinMetrics() {
    var sessionEl = document.querySelector('.twin-metric-val[style*="22C55E"]');
    if (sessionEl) {
      var v = 12000 + Math.floor(Math.random() * 600);
      sessionEl.textContent = v.toLocaleString();
    }
  }
  setInterval(updateTwinMetrics, 4000);
})();

// ── Smooth scroll for footer links ──
document.addEventListener('DOMContentLoaded', function() {
  // Fix hero secondary button scroll
  var heroSecBtn = document.querySelector('.btn-hero-secondary[onclick*="scrollTo"]');
  if (heroSecBtn) {
    heroSecBtn.addEventListener('click', function() {
      var featEl = document.getElementById('all-features');
      if (featEl) featEl.scrollIntoView({ behavior: 'smooth' });
    });
  }
});
</script>
"""

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Inject JS just before </body>
BODY_CLOSE = '</body>\n</html>'
ALT_CLOSE = '</body>'

if BODY_CLOSE in content:
    content = content.replace(BODY_CLOSE, JS_CODE + '\n</body>\n</html>', 1)
    print("SUCCESS: JS injected before </body>")
elif ALT_CLOSE in content:
    idx = content.rfind(ALT_CLOSE)
    content = content[:idx] + JS_CODE + '\n' + content[idx:]
    print("SUCCESS: JS injected via rfind")
else:
    print("ERROR: No </body> found")

with open('Frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
