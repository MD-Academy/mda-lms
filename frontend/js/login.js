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
    forgotModal.style.display = 'flex';
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
        const { data, error } = await db.auth.signInWithPassword({ email, password });

        if (error) {
            if (error.message.includes('Invalid login credentials')) {
                showAlert('Incorrect email or password. Please try again.');
            } else {
                showAlert(`Login failed: ${error.message}`);
            }
            setLoading(false);
            return;
        }

        const userId = data.user.id;

        const { data: profile, error: profileError } = await db
            .from('profiles')
            .select('role, status, expiry_date, full_name')
            .eq('id', userId)
            .single();

        if (profileError || !profile) {
            showAlert('Unable to load your account. Please contact your administrator.');
            await db.auth.signOut();
            setLoading(false);
            return;
        }

        if (profile.status === 'suspended') {
            showAlert('Your account has been suspended. Please contact your administrator.');
            await db.auth.signOut();
            setLoading(false);
            return;
        }

        if (profile.expiry_date) {
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            const expiry = new Date(profile.expiry_date);
            if (expiry < today) {
                showAlert('Your account has expired. Please contact your administrator.');
                await db.auth.signOut();
                setLoading(false);
                return;
            }
        }

        if (profile.role === 'admin') {
            showAlert('Please use the admin portal to sign in.', 'info');
            await db.auth.signOut();
            setLoading(false);
            return;
        }

        window.location.href = 'dashboard.html';

    } catch (err) {
        showAlert('An unexpected error occurred. Please try again.');
        setLoading(false);
    }
});

// Redirect if already logged in
(async () => {
    const { data: { session } } = await db.auth.getSession();
    if (session) {
        const { data: profile } = await db
            .from('profiles')
            .select('role, status, expiry_date')
            .eq('id', session.user.id)
            .single();

        if (profile && profile.role === 'student' && profile.status === 'active') {
            const today = new Date(); today.setHours(0,0,0,0);
            const expired = profile.expiry_date && new Date(profile.expiry_date) < today;
            if (!expired) window.location.href = 'dashboard.html';
        }
    }
})();
