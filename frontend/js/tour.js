// First-login guided tour for the student portal. Shows once (per browser,
// per student), with Next / Back / Skip. Call maybeStartTour(uid) after the
// layout is rendered; it does nothing if the student has already seen it.

(function () {
    const STEPS = [
        { sel: null, title: 'Welcome to your portal 👋', text: "Here's a quick 30-second tour of where everything is. You can skip it any time — it only shows once." },
        { sel: '.nav-item[href="dashboard.html"]', title: '🏠 Dashboard', text: 'Your home screen — your courses, upcoming classes and the latest announcements at a glance.' },
        { sel: '.nav-item[href="courses.html"]', title: '🎓 My Courses', text: 'Open a course to find its subjects — presentations, video lectures and quizzes. Your attendance and grades live here too.' },
        { sel: '.nav-item[href="recordings.html"]', title: '🎥 Zoom Classes', text: 'Join your live classes and watch recordings of past ones.' },
        { sel: '.nav-item[href="feedback.html"]', title: '💬 Messages', text: 'Read feedback your teachers write for you — and message any staff member directly.' },
        { sel: '.nav-item[href="exams.html"]', title: '📝 Exams', text: 'Take your assigned exams here. Results appear in your grades.' },
        { sel: '#notif-bell', title: '🔔 Notifications', text: 'The bell lights up whenever there is something new for you — feedback, a reply, or an announcement.' },
        { sel: '#avatar-btn', title: '👤 Your photo', text: 'Tap your picture to upload a photo. You can change your password under Profile.' },
        { sel: '.nav-item[href="support.html"]', title: '🆘 Help & Support', text: "Stuck on anything? Open a support ticket and the office will help. There's also a full User Guide in the menu." },
        { sel: '.nav-item[href="guide.html"]', title: "You're all set 🎉", text: 'Want to see this again? Open the User Guide any time and tap “Replay the welcome tour”. Welcome aboard, and good luck with your studies!' },
    ];

    let idx = 0, uid = null, ov = null, prevHi = null;

    function key(u) { return 'mda_tour_' + (u || 'anon'); }

    function ensure() {
        if (ov) return;
        ov = document.createElement('div');
        ov.className = 'tour-overlay';
        ov.innerHTML = `
            <div class="tour-card" id="tour-card">
                <button class="tour-skip" id="tour-skip">Skip</button>
                <div class="tour-title" id="tour-title"></div>
                <div class="tour-text" id="tour-text"></div>
                <div class="tour-foot">
                    <div class="tour-dots" id="tour-dots"></div>
                    <div class="tour-btns">
                        <button class="tour-btn ghost" id="tour-back">Back</button>
                        <button class="tour-btn primary" id="tour-next">Next</button>
                    </div>
                </div>
            </div>`;
        document.body.appendChild(ov);
        document.getElementById('tour-skip').onclick = finish;
        document.getElementById('tour-back').onclick = () => { if (idx > 0) { idx--; show(); } };
        document.getElementById('tour-next').onclick = () => { if (idx < STEPS.length - 1) { idx++; show(); } else { finish(); } };
        document.addEventListener('keydown', onKey);
    }

    function onKey(e) {
        if (!ov || !ov.classList.contains('open')) return;
        if (e.key === 'Escape') finish();
        else if (e.key === 'ArrowRight' || e.key === 'Enter') document.getElementById('tour-next').click();
        else if (e.key === 'ArrowLeft') document.getElementById('tour-back').click();
    }

    function clearHi() {
        if (prevHi) { prevHi.classList.remove('tour-highlight'); prevHi = null; }
    }

    function show() {
        const step = STEPS[idx];
        document.getElementById('tour-title').textContent = step.title;
        document.getElementById('tour-text').textContent = step.text;
        document.getElementById('tour-back').style.visibility = idx === 0 ? 'hidden' : 'visible';
        document.getElementById('tour-next').textContent = idx === STEPS.length - 1 ? 'Finish' : 'Next';
        document.getElementById('tour-dots').innerHTML = STEPS.map((_, i) => `<span class="tour-dot ${i === idx ? 'on' : ''}"></span>`).join('');

        clearHi();
        const card = document.getElementById('tour-card');
        const target = step.sel ? document.querySelector(step.sel) : null;
        if (target) {
            target.classList.add('tour-highlight');
            prevHi = target;
            try { target.scrollIntoView({ behavior: 'smooth', block: 'center' }); } catch (e) {}
            positionCard(card, target);
        } else {
            card.classList.add('centered');
            card.style.left = ''; card.style.top = '';
        }
    }

    // Place the card beside the target, always kept fully inside the screen.
    function positionCard(card, target) {
        card.classList.remove('centered');
        card.style.left = '0px'; card.style.top = '0px';   // measure at a known spot
        const vw = window.innerWidth, vh = window.innerHeight, gap = 14, pad = 12;
        const cw = Math.min(card.offsetWidth || 340, vw - pad * 2);
        const ch = card.offsetHeight || 220;
        const r = target.getBoundingClientRect();
        let left, top;
        if (vw - r.right >= cw + gap + pad) {            // room on the right
            left = r.right + gap; top = r.top;
        } else if (r.left >= cw + gap + pad) {           // room on the left
            left = r.left - cw - gap; top = r.top;
        } else if (vh - r.bottom >= ch + gap + pad) {    // room below
            left = r.left + r.width / 2 - cw / 2; top = r.bottom + gap;
        } else {                                          // otherwise above
            left = r.left + r.width / 2 - cw / 2; top = r.top - ch - gap;
        }
        left = Math.max(pad, Math.min(left, vw - cw - pad));
        top = Math.max(pad, Math.min(top, vh - ch - pad));
        card.style.left = left + 'px';
        card.style.top = top + 'px';
    }

    function start() { idx = 0; ensure(); ov.classList.add('open'); show(); }

    function finish() {
        clearHi();
        if (ov) ov.classList.remove('open');
        try { localStorage.setItem(key(uid), '1'); } catch (e) {}
    }

    // Public: start only if this student hasn't seen it.
    window.maybeStartTour = function (userId) {
        uid = userId || null;
        try { if (localStorage.getItem(key(uid))) return; } catch (e) { return; }
        // Let the layout settle first.
        setTimeout(start, 500);
    };
    // Public: force it (e.g. a "Replay tour" button in the guide).
    window.startTour = function (userId) { uid = userId || uid; start(); };
})();
