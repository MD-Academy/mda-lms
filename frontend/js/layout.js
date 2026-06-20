// Student layout — navy sidebar + topbar. Nav grows as more sections are built.

const NAV_ITEMS = [
    { id: 'dashboard', label: 'Dashboard', href: 'dashboard.html', icon: '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>' },
    { id: 'courses', label: 'My Courses', href: 'courses.html', icon: '<path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/>' },
    { id: 'recordings', label: 'Zoom Recordings', href: 'recordings.html', icon: '<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>' },
    { id: 'booklets', label: 'Booklets', href: 'booklets.html', icon: '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/><line x1="12" y1="7" x2="12" y2="21"/>' },
    { id: 'exams', label: 'Exams', href: 'exams.html', icon: '<path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>' },
    { id: 'meetings', label: 'Personal Meetings', href: 'meetings.html', icon: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' },
    { id: 'universities', label: 'University Selection', href: 'universities.html', icon: '<path d="M3 21h18"/><path d="M5 21V10l7-5 7 5v11"/><path d="M9 21v-6h6v6"/>' },
    { id: 'tuition', label: 'Tuition', href: 'tuition.html', icon: '<rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/>' },
    { id: 'support', label: 'Help & Support', href: 'support.html', icon: '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' },
    { id: 'profile', label: 'Profile', href: 'profile.html', icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>' }
];

function _esc(str) {
    if (!str) return '';
    return String(str).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
}

// Breadcrumb trail so students always see where they are and can jump back a step.
// items = [{ label, href? }]; the last item is the current page (shown plain, not linked).
function crumbs(items) {
    return `<nav class="crumbs" aria-label="Breadcrumb">` + items.map((c, i) => {
        const sep = i > 0 ? `<span class="crumb-sep">›</span>` : '';
        const isLast = i === items.length - 1;
        const node = (!isLast && c.href)
            ? `<a class="crumb" href="${c.href}">${_esc(c.label)}</a>`
            : `<span class="crumb-current" aria-current="page">${_esc(c.label)}</span>`;
        return sep + node;
    }).join('') + `</nav>`;
}

function renderLayout(activeId, pageTitle, pageSub, profile) {
    const initials = (profile.full_name || 'S').trim().split(/\s+/).map(w => w[0]).slice(0, 2).join('').toUpperCase();

    const navHtml = NAV_ITEMS.map(item => `
        <a href="${item.href}" class="nav-item ${item.id === activeId ? 'active' : ''}">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${item.icon}</svg>
            ${item.label}
        </a>`).join('');

    document.getElementById('app-layout').innerHTML = `
        <aside class="sidebar">
            <div class="sidebar-logo">
                <img src="assets/images/mda-logo.png" alt="MDA">
                <div class="brand-text">
                    <strong>MDA</strong>
                    <span>Student Portal</span>
                </div>
            </div>
            <nav class="nav-menu">${navHtml}</nav>
            <div class="sidebar-footer">
                <button class="logout-btn" id="logout-btn">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                    Sign Out
                </button>
            </div>
        </aside>
        <div class="main">
            <header class="topbar">
                <div>
                    <h1>${_esc(pageTitle)}</h1>
                    ${pageSub ? `<div class="page-sub">${_esc(pageSub)}</div>` : ''}
                </div>
                <div class="topbar-user">
                    <div class="user-info">
                        <strong style="display:inline-flex;align-items:center;gap:7px;align-self:flex-end;margin-bottom:5px;background:linear-gradient(135deg,#2563eb 0%,#7a2a6b 55%,#b91c5c 100%);color:#fff;font-weight:700;font-size:13.5px;padding:6px 13px;border-radius:10px;text-shadow:0 1px 2px rgba(0,0,0,.22);box-shadow:0 4px 12px rgba(37,99,235,.28),0 2px 4px rgba(185,28,92,.28),inset 0 1px 0 rgba(255,255,255,.38),inset 0 -2px 4px rgba(0,0,0,.18);">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 8l9-4 9 4-9 4-9-4z"/><path d="M21 8v4.5"/><circle cx="12" cy="14.5" r="2.4"/><path d="M7.6 21a4.4 4.4 0 0 1 8.8 0"/></svg>
                            ${_esc(profile.full_name || 'Student')}
                        </strong>
                        <span>Student</span>
                    </div>
                    <button class="avatar avatar-btn" id="avatar-btn" title="Upload a photo">
                        <span class="avatar-inner" id="avatar-inner">${profile.avatar_url ? `<img src="${_esc(profile.avatar_url)}" alt="">` : initials}</span>
                        <span class="avatar-edit">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
                        </span>
                    </button>
                    <input type="file" id="avatar-input" accept="image/png,image/jpeg,image/webp,image/gif" style="display:none">
                </div>
            </header>
            <div class="content" id="page-content"></div>
            <footer style="text-align:center;padding:16px 24px;color:#64748b;font-size:12px;line-height:1.6;border-top:1px solid var(--border);">
                Your personal information is processed in accordance with our <a href="https://www.medicaldoctor-studies.com/privacy-policy/" target="_blank" rel="noopener" style="color:#475569;text-decoration:underline;">Privacy Policy</a>. By continuing to use this platform, you confirm that you have read, understood and agree to it.<br>
                This platform was made by Diego Ilan Tevelev · © Medical Doctor Academy 2026. All rights reserved.
            </footer>
        </div>
    `;

    document.getElementById('logout-btn').addEventListener('click', signOut);
    _setupAvatarUpload();
}

// ── AVATAR / PROFILE PHOTO UPLOAD (topbar) ──
const AVATAR_BUCKET = 'avatars';
const AVATAR_MAX_BYTES = 500 * 1024; // 500 KB
const AVATAR_ALLOWED = ['png', 'jpg', 'jpeg', 'webp', 'gif'];

function _setupAvatarUpload() {
    const btn = document.getElementById('avatar-btn');
    const input = document.getElementById('avatar-input');
    if (!btn || !input) return;

    btn.addEventListener('click', () => input.click());
    input.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        input.value = '';
        if (!file) return;

        const ext = (file.name.split('.').pop() || '').toLowerCase();
        if (!file.type.startsWith('image/') || !AVATAR_ALLOWED.includes(ext)) {
            alertDialog({ title: 'Invalid file', message: 'Please use an image: PNG, JPG, JPEG, WEBP or GIF.', danger: true });
            return;
        }
        if (file.size > AVATAR_MAX_BYTES) {
            alertDialog({ title: 'Image too large', message: `Your image is ${(file.size / 1024).toFixed(0)} KB — the maximum is 500 KB. Please choose a smaller one.`, danger: true });
            return;
        }

        const inner = document.getElementById('avatar-inner');
        const prev = inner.innerHTML;
        inner.innerHTML = '…';
        try {
            const { data: { session } } = await db.auth.getSession();
            if (!session) throw new Error('Not signed in.');
            const userId = session.user.id;
            const path = `${userId}/avatar.${ext}`;

            const up = await db.storage.from(AVATAR_BUCKET).upload(path, file, { contentType: file.type, upsert: true });
            if (up.error) throw new Error(up.error.message);

            const { data: pub } = db.storage.from(AVATAR_BUCKET).getPublicUrl(path);
            const url = `${pub.publicUrl}?t=${Date.now()}`;

            const upd = await db.from('profiles').update({ avatar_url: url }).eq('id', userId);
            if (upd.error) throw new Error(upd.error.message);

            inner.innerHTML = `<img src="${_esc(url)}" alt="">`;
            // Sync the big avatar on the profile page if it's on screen.
            const big = document.getElementById('avatar-big'); if (big) big.innerHTML = `<img src="${_esc(url)}" alt="">`;
        } catch (err) {
            inner.innerHTML = prev;
            alertDialog({ title: 'Upload failed', message: `Could not upload photo: ${err.message}`, danger: true });
        }
    });
}

// ── STYLED DIALOGS (shared across the student portal) ──
// Branded replacements for window.confirm()/alert(). No browser-default popups.
function _ensureDialog() {
    if (document.getElementById('ui-dialog-overlay')) return;
    const style = document.createElement('style');
    style.textContent = `
        .ui-dlg-overlay { position: fixed; inset: 0; background: rgba(10,18,40,0.55); display: none; align-items: center; justify-content: center; z-index: 2000; padding: 20px; }
        .ui-dlg-overlay.open { display: flex; }
        .ui-dlg { background: #fff; border-radius: 16px; width: 100%; max-width: 440px; box-shadow: 0 20px 50px rgba(10,18,40,.3); overflow: hidden; animation: ui-dlg-in .14s ease-out; }
        @keyframes ui-dlg-in { from { transform: translateY(8px); opacity: 0; } to { transform: none; opacity: 1; } }
        .ui-dlg-body { padding: 26px 26px 18px; text-align: center; }
        .ui-dlg-icon { width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 14px; }
        .ui-dlg-icon svg { width: 26px; height: 26px; }
        .ui-dlg-icon.info { background: #e0edff; color: #2563eb; }
        .ui-dlg-icon.danger { background: #fee2e2; color: #dc2626; }
        .ui-dlg-title { font-size: 18px; font-weight: 800; color: #0f2547; margin: 0 0 8px; }
        .ui-dlg-msg { font-size: 14.5px; line-height: 1.55; color: #475569; white-space: pre-line; }
        .ui-dlg-foot { display: flex; gap: 10px; justify-content: center; padding: 0 26px 24px; }
        .ui-dlg-foot .btn { min-width: 110px; justify-content: center; }
        .ui-dlg-foot .btn-danger { background: linear-gradient(135deg, #dc2626, #ef4444); color: #fff; }
        .ui-dlg-foot .btn-danger:hover { opacity: .92; }
    `;
    document.head.appendChild(style);
    const ov = document.createElement('div');
    ov.className = 'ui-dlg-overlay';
    ov.id = 'ui-dialog-overlay';
    ov.innerHTML = `
        <div class="ui-dlg" role="dialog" aria-modal="true">
            <div class="ui-dlg-body">
                <div class="ui-dlg-icon info" id="ui-dlg-icon"></div>
                <h3 class="ui-dlg-title" id="ui-dlg-title"></h3>
                <div class="ui-dlg-msg" id="ui-dlg-msg"></div>
            </div>
            <div class="ui-dlg-foot" id="ui-dlg-foot"></div>
        </div>`;
    document.body.appendChild(ov);
}

const _UI_ICON_DANGER = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
const _UI_ICON_INFO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';

// confirmDialog -> Promise<boolean>. alertDialog -> Promise<void> (single button).
function _showDialog({ title, message, confirmText, cancelText, danger, oneButton }) {
    _ensureDialog();
    const ov = document.getElementById('ui-dialog-overlay');
    const icon = document.getElementById('ui-dlg-icon');
    const foot = document.getElementById('ui-dlg-foot');
    document.getElementById('ui-dlg-title').textContent = title;
    document.getElementById('ui-dlg-msg').textContent = message || '';
    icon.className = 'ui-dlg-icon ' + (danger ? 'danger' : 'info');
    icon.innerHTML = danger ? _UI_ICON_DANGER : _UI_ICON_INFO;

    foot.innerHTML = oneButton
        ? `<button class="btn btn-primary" id="ui-dlg-ok">${confirmText || 'OK'}</button>`
        : `<button class="btn btn-ghost" id="ui-dlg-cancel">${cancelText || 'Cancel'}</button>
           <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" id="ui-dlg-ok">${confirmText || 'Confirm'}</button>`;
    ov.classList.add('open');

    return new Promise(resolve => {
        const okBtn = document.getElementById('ui-dlg-ok');
        const cancelBtn = document.getElementById('ui-dlg-cancel');
        function cleanup(result) {
            ov.classList.remove('open');
            document.removeEventListener('keydown', onKey);
            ov.onclick = null;
            resolve(result);
        }
        function onKey(e) {
            if (e.key === 'Escape' && !oneButton) cleanup(false);
            else if (e.key === 'Enter') cleanup(true);
        }
        okBtn.onclick = () => cleanup(true);
        if (cancelBtn) cancelBtn.onclick = () => cleanup(false);
        ov.onclick = (e) => { if (e.target === ov && !oneButton) cleanup(false); };
        document.addEventListener('keydown', onKey);
        okBtn.focus();
    });
}

function confirmDialog(opts = {}) { return _showDialog({ ...opts, oneButton: false }); }
function alertDialog(opts = {}) { return _showDialog({ ...opts, oneButton: true }); }
