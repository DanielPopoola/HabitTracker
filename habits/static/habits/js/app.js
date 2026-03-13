// ─── Render ───────────────────────────────────────────────────────────────────

async function render() {
    renderSummary();
    await renderHabitList();
    renderArchivedList();
}
function renderSummary() {
    const s = state.summary;
    document.getElementById('summary-total').textContent = s.total_habits ?? '—';
    document.getElementById('summary-completions').textContent = s.total_completions ?? '—';
    document.getElementById('summary-streaks').textContent = s.habits_on_streak ?? '—';
    document.getElementById('summary-broken').textContent = s.habits_broken ?? '—';
}

async function renderHabitList() {
    const list = document.getElementById('habit-list');
    const empty = document.getElementById('empty-state');

    if (state.habits.length === 0) {
        list.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');

    const periodData = await Promise.all(
        state.habits.map(h => habits.analytics(h.id))
    );

    list.innerHTML = state.habits
        .map((habit, i) => habitCard(habit, periodData[i]))
        .join('');
}

function habitCard(habit, periods = []) {
    const dots = periods.slice(0, 30).map(p => {
        const cls = p.status === 'COMPLETED' ? 'dot-completed'
                  : p.status === 'FAILED'    ? 'dot-failed'
                  : 'dot-active';
        return `<span class="dot ${cls}" title="${p.key}"></span>`;
    }).join('');

    return `
        <div class="habit-card" data-id="${habit.id}">
            <div class="habit-card-header">
                <span class="habit-task">${habit.task_specification}</span>
                <span class="habit-periodicity">${habit.periodicity}</span>
            </div>
            <div class="habit-dots">${dots}</div>
            <div class="habit-card-footer">
                <button class="btn-done" data-id="${habit.id}">✓ Done</button>
                <button class="btn-archive" data-id="${habit.id}">Archive</button>
            </div>
        </div>
    `;
}

function archivedCard(habit) {
    return `
        <div class="habit-card habit-card-archived" data-id="${habit.id}">
            <div class="habit-card-header">
                <span class="habit-task">${habit.task_specification}</span>
                <span class="habit-periodicity">${habit.periodicity}</span>
            </div>
            <div class="habit-card-footer">
                <button class="btn-unarchive" data-id="${habit.id}">Unarchive</button>
            </div>
        </div>
    `;
}

function renderArchivedList() {
    const list = document.getElementById('archived-list');
    if (state.archivedHabits.length === 0) {
        list.innerHTML = '<p class="empty-archived">No archived habits.</p>';
        return;
    }
    list.innerHTML = state.archivedHabits.map(archivedCard).join('');
}

// ─── Page load ────────────────────────────────────────────────────────────────

async function init() {
    try {
        const [me, summary, habitData] = await Promise.all([
            auth.me(),
            analytics.summary(),
            habits.list(),
        ]);

        document.getElementById('header-username').textContent = me.username;

        setState({
            habits: habitData.results,
            summary,
        });

    } catch (err) {
        // auth.me() 401/403 already redirects in apiFetch
        // this catches any other load error
        console.error('Failed to load dashboard:', err);
    }
}

async function handleComplete(id) {
    try {
        await completions.create(id);
        const updated = await habits.retrieve(id);
        setState({
            habits: state.habits.map(h => h.id === id ? updated : h),
        });
        await refreshSummary();
    } catch (err) {
        console.error('Failed to complete habit:', err);
    }
}

async function handleArchive(id) {
    try {
        const updated = await habits.archive(id);
        setState({
            habits: state.habits.filter(h => h.id !== id),
            archivedHabits: [updated, ...state.archivedHabits],
        });
        await refreshSummary();
    } catch (err) {
        console.error('Failed to archive habit:', err);
    }
}


async function handleUnarchive(id) {
    try {
        const updated = await habits.unarchive(id);
        setState({
            habits: [updated, ...state.habits],
            archivedHabits: state.archivedHabits.filter(h => h.id !== id),
        });
        await refreshSummary();
    } catch (err) {
        console.error('Failed to unarchive habit:', err);
    }
}

async function refreshSummary() {
    const summary = await analytics.summary();
    setState({ summary });
}

// ─── Event listeners ──────────────────────────────────────────────────────────

document.getElementById('btn-logout').addEventListener('click', async () => {
    await auth.logout();
    window.location.href = '/login/';
});

document.getElementById('btn-export').addEventListener('click', () => {
    analytics.export('csv');
});

document.getElementById('btn-add').addEventListener('click', () => {
    document.getElementById('modal-add').classList.remove('hidden');
});

document.getElementById('btn-modal-cancel').addEventListener('click', () => {
    document.getElementById('modal-add').classList.add('hidden');
    document.getElementById('modal-error').classList.add('hidden');
    document.getElementById('form-add-habit').reset();
});


document.getElementById('form-add-habit').addEventListener('submit', async (e) => {
    e.preventDefault();
    const task = document.getElementById('input-task').value.trim();
    const periodicity = document.getElementById('input-periodicity').value;

    try {
        const habit = await habits.create(task, periodicity);
        document.getElementById('modal-add').classList.add('hidden');
        document.getElementById('form-add-habit').reset();
        setState({ habits: [habit, ...state.habits] });
    } catch (err) {
        document.getElementById('modal-error').textContent = err.message;
        document.getElementById('modal-error').classList.remove('hidden');
    }
});

document.getElementById('habit-list').addEventListener('click', async (e) => {
    const id = e.target.dataset.id;
    if (!id) return;

    if (e.target.classList.contains('btn-done')) {
        await handleComplete(id);
    }

    if (e.target.classList.contains('btn-archive')) {
        await handleArchive(id);
    }
});

document.getElementById('btn-toggle-archived').addEventListener('click', () => {
    const list = document.getElementById('archived-list');
    const btn = document.getElementById('btn-toggle-archived');
    const isHidden = list.classList.toggle('hidden');
    btn.textContent = isHidden ? 'Show archived habits' : 'Hide archived habits';
});

document.getElementById('archived-list').addEventListener('click', async (e) => {
    const id = e.target.dataset.id;
    if (!id) return;

    if (e.target.classList.contains('btn-unarchive')) {
        await handleUnarchive(id);
    }
});
// ─── Boot ─────────────────────────────────────────────────────────────────────

init();