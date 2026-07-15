// Student auth, session guard, login-time tracking, and backend calls.

const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

function _isStudentActive(p) {
    if (!p || p.role !== 'student' || p.status === 'suspended') return false;
    if (p.expiry_date) {
        const today = new Date(); today.setHours(0, 0, 0, 0);
        if (new Date(p.expiry_date) < today) return false;
    }
    return true;
}

// Gate every student page. Redirects inactive/suspended/expired users to login.
async function requireStudent() {
    const { data: { session } } = await db.auth.getSession();
    if (!session) { window.location.href = 'index.html'; return null; }

    const { data: profile, error: profErr } = await db
        .from('profiles')
        .select('role, full_name, avatar_url, status, expiry_date')
        .eq('id', session.user.id)
        .single();

    // A failed lookup is NOT proof the account is inactive — never sign out on a transient error.
    if (profErr) {
        console.error('[auth] could not verify account:', profErr);
        const el = document.getElementById('app-layout') || document.body;
        el.innerHTML = `<div style="max-width:440px;margin:120px auto;text-align:center;font-family:'Inter',sans-serif;color:#1e293b;padding:0 20px;">
            <h2 style="margin-bottom:10px;">Connection problem</h2>
            <p style="color:#64748b;">We couldn't verify your account right now. Please refresh — if it keeps happening, contact the office.</p>
            <button onclick="location.reload()" style="margin-top:18px;padding:10px 20px;border:none;border-radius:8px;background:#1e3a8a;color:#fff;font-weight:600;cursor:pointer;">Refresh</button>
        </div>`;
        return null;
    }

    if (!_isStudentActive(profile)) {
        await _endSession();
        await db.auth.signOut();
        window.location.href = 'index.html?inactive=1';
        return null;
    }
    // Enforce 2FA: if enrolled but not completed this session, return to login to finish it.
    try {
        const { data: aal } = await db.auth.mfa.getAuthenticatorAssuranceLevel();
        if (aal && aal.nextLevel === 'aal2' && aal.currentLevel !== 'aal2') { window.location.href = 'index.html'; return null; }
    } catch (e) { /* ignore */ }

    _startStudentWatch(session.user.id);
    _startLoginTracking(session.user.id);
    await _enforceContentPolicy(session);
    return { session, profile };
}

// One-time content-use agreement. Blocks until accepted; recorded per account.
async function _enforceContentPolicy(session) {
    if (sessionStorage.getItem('mda_policy_ok') === '1') return;
    try {
        const { data } = await db.from('policy_acceptances').select('student_id').eq('student_id', session.user.id).limit(1);
        if (data && data.length) { sessionStorage.setItem('mda_policy_ok', '1'); return; }
    } catch (e) { return; }   // if the table isn't there yet, don't block the portal

    await new Promise(resolve => {
        const ov = document.createElement('div');
        ov.id = 'policy-overlay';
        ov.style.cssText = 'position:fixed;inset:0;background:rgba(6,12,28,.78);display:flex;align-items:center;justify-content:center;z-index:99999;padding:20px;font-family:Inter,system-ui,sans-serif;';
        ov.innerHTML = `<div style="background:#fff;border-radius:16px;max-width:520px;width:100%;padding:26px 26px 22px;box-shadow:0 20px 60px rgba(0,0,0,.4);">
            <h2 style="margin:0 0 12px;font-size:20px;color:#0a1e3d;">Content use agreement</h2>
            <p style="font-size:14px;line-height:1.6;color:#334155;margin:0 0 12px;">All lectures, recordings, presentations and materials in this portal are the property of Medical Doctor Academy and are provided for your <strong>personal study only</strong>.</p>
            <ul style="font-size:13.5px;line-height:1.7;color:#334155;margin:0 0 14px;padding-left:18px;">
                <li>Every page and video is <strong>watermarked and traced to your account</strong>.</li>
                <li><strong>Recording, screen-capturing, downloading, copying or sharing</strong> any content is strictly prohibited.</li>
                <li>Violations are grounds for <strong>removal from the programme</strong> and possible legal action.</li>
            </ul>
            <label style="display:flex;align-items:center;gap:9px;font-size:13.5px;color:#334155;margin-bottom:16px;cursor:pointer;"><input type="checkbox" id="policy-check" style="width:18px;height:18px;flex-shrink:0;"> I have read and agree to these terms.</label>
            <button id="policy-agree" disabled style="width:100%;padding:12px;border:none;border-radius:10px;background:#9aa5b5;color:#fff;font-weight:700;font-size:14px;cursor:not-allowed;">Continue</button>
        </div>`;
        document.body.appendChild(ov);
        const chk = ov.querySelector('#policy-check'), btn = ov.querySelector('#policy-agree');
        chk.addEventListener('change', () => {
            btn.disabled = !chk.checked;
            btn.style.background = chk.checked ? 'linear-gradient(135deg,#1a4a8a,#b91c5c)' : '#9aa5b5';
            btn.style.cursor = chk.checked ? 'pointer' : 'not-allowed';
        });
        btn.addEventListener('click', async () => {
            btn.disabled = true; btn.textContent = 'Saving…';
            try { await db.from('policy_acceptances').upsert({ student_id: session.user.id, version: 'v1', accepted_at: new Date().toISOString() }, { onConflict: 'student_id' }); } catch (e) { /* proceed anyway */ }
            sessionStorage.setItem('mda_policy_ok', '1');
            ov.remove();
            resolve();
        });
    });
}

// Periodic check: kick a student who gets suspended/expired while logged in.
let _studentWatchTimer = null;
function _startStudentWatch(userId) {
    if (_studentWatchTimer) clearInterval(_studentWatchTimer);
    _studentWatchTimer = setInterval(async () => {
        try {
            const { data: { session } } = await db.auth.getSession();
            if (!session) { window.location.href = 'index.html'; return; }
            const { data: p, error: pErr } = await db.from('profiles').select('role, status, expiry_date').eq('id', session.user.id).single();
            if (pErr) { console.error('[auth] account watch check failed (will retry):', pErr); return; }  // transient — don't kick on a blip
            if (!_isStudentActive(p)) {
                await _endSession();
                await db.auth.signOut();
                window.location.href = 'index.html?inactive=1';
            }
        } catch (e) { /* ignore transient */ }
    }, 60000);
}

// ── LOGIN-TIME TRACKING (silent; data is admin-only) ──
let _heartbeatTimer = null;
async function _startLoginTracking(studentId) {
    try {
        let sid = sessionStorage.getItem('mda_login_session_id');
        if (!sid) {
            const { data, error } = await db.from('login_sessions').insert({ student_id: studentId }).select('id').single();
            if (error) return;
            sid = data.id;
            sessionStorage.setItem('mda_login_session_id', sid);
        } else {
            // Reusing this browser's session across page navigations — keep it OPEN
            // (clear any end stamp) so the student still counts as active.
            db.from('login_sessions').update({ last_seen_at: new Date().toISOString(), ended_at: null }).eq('id', sid);
        }
        if (_heartbeatTimer) clearInterval(_heartbeatTimer);
        _heartbeatTimer = setInterval(() => {
            const id = sessionStorage.getItem('mda_login_session_id');
            if (id) db.from('login_sessions').update({ last_seen_at: new Date().toISOString(), ended_at: null }).eq('id', id);
        }, 60000);

        // On unload, just bump "last seen" — do NOT end the session, because normal
        // page navigation fires this too. The session ends only on sign-out (below).
        window.addEventListener('beforeunload', () => {
            const id = sessionStorage.getItem('mda_login_session_id');
            if (id) db.from('login_sessions').update({ last_seen_at: new Date().toISOString() }).eq('id', id);
        });
        // Keep the session fresh as the student moves between tabs/windows. When
        // they come back to the portal tab, immediately refresh it (and keep it
        // open) so background-tab timer throttling doesn't make it look "ended".
        const _touch = (keepOpen) => {
            const id = sessionStorage.getItem('mda_login_session_id');
            if (!id) return;
            const patch = { last_seen_at: new Date().toISOString() };
            if (keepOpen) patch.ended_at = null;
            db.from('login_sessions').update(patch).eq('id', id);
        };
        document.addEventListener('visibilitychange', () => _touch(document.visibilityState === 'visible'));
        window.addEventListener('focus', () => _touch(true));
    } catch (e) { /* tracking must never block the page */ }
}

async function _endSession() {
    const sid = sessionStorage.getItem('mda_login_session_id');
    if (sid) {
        try { await db.from('login_sessions').update({ last_seen_at: new Date().toISOString(), ended_at: new Date().toISOString() }).eq('id', sid); } catch (e) {}
        sessionStorage.removeItem('mda_login_session_id');
    }
    if (_heartbeatTimer) clearInterval(_heartbeatTimer);
}

async function signOut() {
    await _endSession();
    await db.auth.signOut();
    window.location.href = 'index.html';
}

// Authenticated call to the FastAPI backend (signed URLs, quiz/exam grading).
async function apiRequest(method, path, body = null) {
    const { data: { session } } = await db.auth.getSession();
    if (!session) throw new Error('Not signed in');
    const opts = {
        method,
        headers: { 'Authorization': `Bearer ${session.access_token}`, 'Content-Type': 'application/json' }
    };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${BACKEND_URL}${path}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
}
