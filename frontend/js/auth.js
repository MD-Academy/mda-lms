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
    return { session, profile };
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
