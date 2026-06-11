const { createClient } = supabase;
const db = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

const loginForm   = document.getElementById('login-form');
const emailInput  = document.getElementById('email-input');
const pwInput     = document.getElementById('password-input');
const togglePw    = document.getElementById('toggle-pw');
const eyeShow     = document.getElementById('eye-show');
const eyeHide     = document.getElementById('eye-hide');
const signinBtn   = document.getElementById('signin-btn');
const btnText     = document.getElementById('btn-text');
const btnArrow    = document.getElementById('btn-arrow');
const alertBox    = document.getElementById('alert-box');
const forgotLink  = document.getElementById('forgot-link');
const forgotModal = document.getElementById('forgot-modal');
const modalClose  = document.getElementById('modal-close');

function showAlert(message, type = 'error') {
    alertBox.className = `alert ${type}`;
    alertBox.textContent = message;
    alertBox.style.display = 'block';
}

function hideAlert() {
    alertBox.style.display = 'none';
}

function setLoading(loading) {
    signinBtn.disabled = loading;
    btnText.textContent = loading ? 'Signing in…' : 'Sign In';
    btnArrow.style.display = loading ? 'none' : 'block';
}

togglePw.addEventListener('click', () => {
    const isHidden = pwInput.type === 'password';
    pwInput.type = isHidden ? 'text' : 'password';
    eyeShow.style.display = isHidden ? 'none' : 'block';
    eyeHide.style.display = isHidden ? 'block' : 'none';
});

forgotLink.addEventListener('click', (e) => {
    e.preventDefault();
    window.location.href = 'reset.html';
});

modalClose.addEventListener('click', () => {
    forgotModal.style.display = 'none';
});

forgotModal.addEventListener('click', (e) => {
    if (e.target === forgotModal) forgotModal.style.display = 'none';
});

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideAlert();

    const email    = emailInput.value.trim();
    const password = pwInput.value;

    if (!email || !password) {
        showAlert('Please enter your email and password.');
        return;
    }

    setLoading(true);

    try {
        const { error } = await db.auth.signInWithPassword({ email, password });
        if (error) {
            showAlert(error.message.includes('Invalid login credentials') ? 'Incorrect email or password. Please try again.' : `Login failed: ${error.message}`);
            setLoading(false);
            return;
        }
        if (await mfaNeeded()) { setLoading(false); promptMfa(); return; }
        await proceedAfterAuth();
    } catch (err) {
        showAlert('An unexpected error occurred. Please try again.');
        setLoading(false);
    }
});

async function proceedAfterAuth() {
    setLoading(true);
    try {
        const { data: { session } } = await db.auth.getSession();
        if (!session) { showAlert('Session error. Please try again.'); setLoading(false); return; }
        const { data: profile, error: profileError } = await db.from('profiles').select('role, status, expiry_date').eq('id', session.user.id).single();
        if (profileError || !profile) {
            showAlert('Unable to load your account. Please contact your administrator.');
            await db.auth.signOut(); setLoading(false); return;
        }
        if (profile.role !== 'student') {
            showAlert('Please use the admin portal to sign in.', 'info');
            await db.auth.signOut(); setLoading(false); return;
        }
        if (profile.status === 'suspended') {
            showAlert('Your account has been suspended. Please contact your administrator.');
            await db.auth.signOut(); setLoading(false); return;
        }
        if (profile.expiry_date) {
            const today = new Date(); today.setHours(0, 0, 0, 0);
            if (new Date(profile.expiry_date) < today) {
                showAlert('Your account has expired. Please contact your administrator.');
                await db.auth.signOut(); setLoading(false); return;
            }
        }
        window.location.href = 'dashboard.html';
    } catch (err) {
        showAlert('An unexpected error occurred. Please try again.');
        setLoading(false);
    }
}

function promptMfa() {
    loginForm.style.display = 'none';
    hideAlert();
    let step = document.getElementById('mfa-step');
    if (!step) {
        step = document.createElement('div');
        step.id = 'mfa-step';
        step.innerHTML = `
            <p style="font-size:14px;color:#374151;margin-bottom:12px;">Two-factor authentication is on. Enter the 6-digit code from your authenticator app.</p>
            <div class="input-row" style="margin-bottom:14px;"><input type="text" id="mfa-code" inputmode="numeric" maxlength="6" placeholder="123456" autocomplete="one-time-code"></div>
            <button type="button" class="btn-signin" id="mfa-verify"><span>Verify</span></button>`;
        loginForm.parentNode.insertBefore(step, loginForm.nextSibling);
        document.getElementById('mfa-verify').addEventListener('click', async () => {
            const code = document.getElementById('mfa-code').value.trim();
            if (!/^\d{6}$/.test(code)) { showAlert('Enter the 6-digit code from your app.'); return; }
            const vbtn = document.getElementById('mfa-verify'); vbtn.disabled = true; vbtn.querySelector('span').textContent = 'Verifying…';
            try { await mfaVerifyCode(code); await proceedAfterAuth(); }
            catch (err) { showAlert(err.message); vbtn.disabled = false; vbtn.querySelector('span').textContent = 'Verify'; }
        });
    }
    step.style.display = 'block';
}

// If a student was kicked out (suspended/expired) mid-session, explain why.
if (new URLSearchParams(window.location.search).get('inactive')) {
    showAlert('Your account is inactive. Please contact the administrator.', 'error');
}

// Redirect if already logged in
(async () => {
    const { data: { session } } = await db.auth.getSession();
    if (!session) return;
    if (await mfaNeeded()) { promptMfa(); return; }
    const { data: profile } = await db.from('profiles').select('role, status, expiry_date').eq('id', session.user.id).single();
    if (profile && profile.role === 'student' && profile.status === 'active') {
        const today = new Date(); today.setHours(0,0,0,0);
        const expired = profile.expiry_date && new Date(profile.expiry_date) < today;
        if (!expired) window.location.href = 'dashboard.html';
    }
})();
