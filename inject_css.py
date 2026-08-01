import sys
sys.stdout.reconfigure(encoding='utf-8')

NEW_CSS = """
/* ═══════════════════════════════════════════
   LANDING PAGE ENHANCEMENTS — NEW SECTIONS
═══════════════════════════════════════════ */

/* ── Status Bar ── */
.status-chip {
  display: flex; align-items: center; gap: 8px;
  font-size: 12px; font-weight: 600; color: var(--text2);
  padding: 6px 14px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.07);
  border-radius: 20px;
  transition: border-color .3s, background .3s;
}
.status-chip:hover { border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.06); }
.status-dot {
  width: 7px; height: 7px; border-radius: 50%;
  animation: blink-dot 2s infinite;
}
@keyframes blink-dot { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ── Feature Cards V2 ── */
.feat-card-v2 {
  position: relative;
  background: linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  transition: transform .3s, box-shadow .3s, border-color .3s;
  overflow: hidden;
}
.feat-card-v2::before {
  content: '';
  position: absolute; inset: 0;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--glow, #4F46E5), transparent 60%);
  opacity: 0;
  transition: opacity .3s;
}
.feat-card-v2:hover {
  transform: translateY(-6px);
  border-color: color-mix(in srgb, var(--glow, #4F46E5) 50%, transparent);
  box-shadow: 0 12px 40px -10px color-mix(in srgb, var(--glow, #4F46E5) 30%, transparent);
}
.feat-card-v2:hover::before { opacity: 0.07; }
.feat-v2-icon {
  font-size: 30px; margin-bottom: 14px; display: block;
  filter: drop-shadow(0 0 8px color-mix(in srgb, var(--glow, #4F46E5) 60%, transparent));
}
.feat-v2-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 15px; font-weight: 700;
  margin-bottom: 8px; color: var(--text);
}
.feat-v2-desc {
  font-size: 12.5px; color: var(--text2); line-height: 1.6; margin-bottom: 14px;
}
.feat-badge {
  display: inline-block;
  font-size: 10px; font-weight: 700; letter-spacing: 1px;
  padding: 3px 10px; border-radius: 20px;
  border: 1px solid currentColor;
}

/* ── How It Works V2 ── */
.hiw-grid {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
}
.hiw-step {
  flex: 1; min-width: 130px; max-width: 180px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 16px;
  text-align: center;
  transition: transform .3s, border-color .3s, box-shadow .3s;
}
.hiw-step:hover {
  transform: translateY(-6px);
  border-color: rgba(79,70,229,0.4);
  box-shadow: 0 8px 30px -8px rgba(79,70,229,0.3);
}
.hiw-num {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 11px; font-weight: 800; letter-spacing: 2px;
  color: var(--text3); margin-bottom: 10px;
}
.hiw-icon {
  font-size: 28px; margin-bottom: 10px; display: block;
}
.hiw-title {
  font-size: 13px; font-weight: 700; margin-bottom: 8px;
}
.hiw-desc {
  font-size: 11px; color: var(--text2); line-height: 1.5;
}
.hiw-arrow {
  font-size: 24px; color: var(--text3);
  padding: 0 4px; align-self: center;
  flex-shrink: 0;
}
@media (max-width: 640px) {
  .hiw-arrow { display: none; }
  .hiw-step { min-width: 140px; }
}

/* ── Tech Stack ── */
.tech-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 16px;
}
.tech-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 20px;
  text-align: center;
  transition: transform .3s, border-color .3s, box-shadow .3s;
  cursor: default;
}
.tech-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--tc, #4F46E5) 50%, transparent);
  box-shadow: 0 8px 24px -8px color-mix(in srgb, var(--tc, #4F46E5) 25%, transparent);
}
.tech-logo {
  font-size: 28px; margin-bottom: 10px; display: block;
}
.tech-name {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 13px; font-weight: 700; margin-bottom: 4px;
}
.tech-desc {
  font-size: 11px; color: var(--text3);
}

/* ── Smart City / Digital Twin ── */
.smart-feat {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px;
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 12px;
  transition: border-color .3s;
}
.smart-feat:hover { border-color: rgba(6,182,212,0.3); }
.smart-feat-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.twin-preview { position: relative; }
.twin-card {
  background: rgba(13,21,32,0.9);
  border: 1px solid rgba(6,182,212,0.2);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(6,182,212,0.1);
}
.twin-header {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  background: rgba(6,182,212,0.06);
  border-bottom: 1px solid rgba(6,182,212,0.15);
  font-size: 12px; font-weight: 600; color: var(--text2);
}
.twin-metrics {
  display: grid; grid-template-columns: repeat(2,1fr);
  gap: 1px; background: rgba(255,255,255,0.04);
  border-bottom: 1px solid var(--border);
}
.twin-metric {
  padding: 16px; background: rgba(13,21,32,0.9);
  text-align: center;
}
.twin-metric-val {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 22px; font-weight: 800; margin-bottom: 4px;
}
.twin-metric-lbl { font-size: 10px; color: var(--text3); letter-spacing: .5px; }
.twin-bar-row {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 8px; font-size: 11px; color: var(--text2);
}
.twin-bar-row > span:first-child { width: 80px; flex-shrink: 0; }
.twin-bar {
  flex: 1; height: 6px;
  background: rgba(255,255,255,0.06);
  border-radius: 3px; overflow: hidden;
}
.twin-bar > div { height: 100%; border-radius: 3px; }
.twin-bar-row > span:last-child { width: 28px; text-align: right; flex-shrink: 0; font-weight: 700; }
@media (max-width: 768px) {
  #smart-city .section-wrap > div { grid-template-columns: 1fr !important; }
}

/* ── Comparison Table ── */
.cmp-table {
  width: 100%;
  border-collapse: collapse;
  background: rgba(255,255,255,0.02);
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid var(--border);
  font-size: 13px;
}
.cmp-table th {
  padding: 14px 20px;
  background: rgba(255,255,255,0.04);
  font-family: 'Space Grotesk', sans-serif;
  font-size: 13px; font-weight: 700;
  border-bottom: 1px solid var(--border);
  color: var(--text);
}
.cmp-table td {
  padding: 12px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
  color: var(--text2);
}
.cmp-table tr:last-child td { border-bottom: none; }
.cmp-table tr:hover td { background: rgba(255,255,255,0.02); }
.cmp-our { background: rgba(79,70,229,0.06) !important; }
.cmp-yes { color: #22C55E !important; font-weight: 600; text-align: center; }
.cmp-no  { color: #EF4444 !important; text-align: center; }
.cmp-partial { color: #F59E0B !important; text-align: center; }

/* ── Project Statistics ── */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.stat-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 16px;
  text-align: center;
  transition: transform .3s, border-color .3s;
}
.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(79,70,229,0.3);
}
.stat-val {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 32px; font-weight: 900;
  line-height: 1; margin-bottom: 8px;
}
.stat-lbl {
  font-size: 12px; color: var(--text3); font-weight: 500;
}

/* ── Testimonials ── */
.testi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
  gap: 20px;
}
.testi-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  display: flex; flex-direction: column; gap: 16px;
  transition: transform .3s, border-color .3s, box-shadow .3s;
}
.testi-card:hover {
  transform: translateY(-4px);
  border-color: rgba(79,70,229,0.3);
  box-shadow: 0 10px 30px -10px rgba(79,70,229,0.2);
}
.testi-quote {
  font-size: 13.5px; color: var(--text2); line-height: 1.7;
  font-style: italic; flex: 1;
}
.testi-quote::before { content: '"'; font-size: 28px; color: var(--primary); line-height: 0; vertical-align: -12px; margin-right: 4px; }
.testi-author {
  display: flex; align-items: center; gap: 12px;
}
.testi-avatar {
  width: 42px; height: 42px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 800; color: #fff;
  flex-shrink: 0;
}
.testi-name { font-weight: 700; font-size: 14px; }
.testi-role { font-size: 11px; color: var(--text3); margin-top: 2px; }
.testi-stars { color: #F59E0B; font-size: 14px; letter-spacing: 2px; }

/* ── Team ── */
.team-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 28px 24px;
  text-align: center;
  transition: transform .3s, border-color .3s;
}
.team-card:hover { transform: translateY(-4px); border-color: rgba(79,70,229,0.3); }
.team-avatar {
  width: 64px; height: 64px; border-radius: 18px;
  margin: 0 auto 16px;
  display: flex; align-items: center; justify-content: center;
  font-size: 28px;
}
.team-name {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 16px; font-weight: 700; margin-bottom: 4px;
}
.team-role { font-size: 12px; color: var(--accent); margin-bottom: 10px; font-weight: 600; }
.team-desc { font-size: 11.5px; color: var(--text3); line-height: 1.5; }

/* ── FAQ ── */
.faq-list { display: flex; flex-direction: column; gap: 10px; }
.faq-item {
  background: rgba(255,255,255,0.02);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color .3s;
}
.faq-item:hover, .faq-item.open { border-color: rgba(79,70,229,0.4); }
.faq-q {
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 20px;
  font-weight: 600; font-size: 14px;
  user-select: none;
}
.faq-arrow {
  font-size: 12px; color: var(--text3);
  transition: transform .3s;
  flex-shrink: 0; margin-left: 12px;
}
.faq-item.open .faq-arrow { transform: rotate(180deg); }
.faq-a {
  max-height: 0; overflow: hidden;
  font-size: 13px; color: var(--text2); line-height: 1.7;
  transition: max-height .4s ease, padding .3s;
  padding: 0 20px;
}
.faq-item.open .faq-a {
  max-height: 300px;
  padding: 0 20px 18px;
}

/* ── Footer ── */
#site-footer {
  border-top: 1px solid var(--border);
  padding: clamp(40px,6vw,72px) 0 0;
  position: relative; z-index: 1;
}
.footer-grid {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr 1fr;
  gap: 40px;
  padding-bottom: 40px;
}
.footer-col-title {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 12px; font-weight: 700;
  letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text3); margin-bottom: 16px;
}
.footer-link {
  display: block; font-size: 13px; color: var(--text3);
  text-decoration: none; margin-bottom: 10px;
  transition: color .2s;
  cursor: pointer; background: none; border: none;
}
.footer-link:hover { color: var(--text); }
.footer-tech {
  display: inline-block; font-size: 11px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 6px; padding: 3px 8px;
  margin: 0 4px 6px 0; color: var(--text3);
}
.social-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 36px; height: 36px; border-radius: 10px;
  background: rgba(255,255,255,0.05);
  border: 1px solid var(--border);
  font-size: 16px; text-decoration: none;
  transition: border-color .2s, background .2s, transform .2s;
}
.social-icon:hover {
  border-color: rgba(79,70,229,0.4);
  background: rgba(79,70,229,0.1);
  transform: translateY(-2px);
}
.footer-bottom {
  border-top: 1px solid var(--border);
  padding: 20px 0;
  display: flex; align-items: center; justify-content: space-between;
  flex-wrap: wrap; gap: 12px;
  font-size: 12px; color: var(--text3);
}
.back-top-btn {
  background: rgba(79,70,229,0.1);
  border: 1px solid rgba(79,70,229,0.3);
  border-radius: 8px;
  color: var(--primary); font-size: 12px; font-weight: 600;
  padding: 6px 14px; cursor: pointer;
  transition: background .2s, transform .2s;
}
.back-top-btn:hover { background: rgba(79,70,229,0.2); transform: translateY(-2px); }

/* ── Fade-in animation ── */
.fade-in-up {
  opacity: 0;
  transform: translateY(30px);
  animation: fade-in-up .6s ease forwards;
}
@keyframes fade-in-up {
  to { opacity:1; transform:translateY(0); }
}

/* ── Responsive tweaks ── */
@media (max-width: 900px) {
  .footer-grid { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 560px) {
  .footer-grid { grid-template-columns: 1fr; }
  .hiw-grid { gap: 12px; }
  .cmp-table { font-size: 11px; }
  .cmp-table th, .cmp-table td { padding: 10px 10px; }
}

/* ── Counter animation for stat cards ── */
[data-target] { transition: color .5s; }
"""

with open('Frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

INJECT_AFTER = '</style>\n<style>\n/* ═══════════════════════════════════════════\n   ANIMATED BACKGROUND'

if INJECT_AFTER in content:
    content = content.replace(INJECT_AFTER, NEW_CSS + '\n' + INJECT_AFTER, 1)
    print("SUCCESS: CSS injected")
else:
    # Try alternative insertion point - before closing </style> of last style block
    # Find any </style> followed by <style> and insert before the last one
    last_style_close = content.rfind('</style>')
    if last_style_close > -1:
        content = content[:last_style_close] + NEW_CSS + '\n</style>' + content[last_style_close+8:]
        print("SUCCESS: CSS injected via fallback")
    else:
        print("ERROR: Could not find injection point")

with open('Frontend/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
