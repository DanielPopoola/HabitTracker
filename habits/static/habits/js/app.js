let errorTimer = null;

async function render() {
    renderErrorBanner();
    renderSummary();
    await renderHabitList();
    renderArchivedList();
    renderDetailPanel();
}

function renderErrorBanner() {
    const banner = document.getElementById('error-banner');
    const message = document.getElementById('error-banner-message');
    if (!state.error) {
        banner.classList.add('hidden');
        return;
    }
    message.textContent = state.error;
    banner.classList.remove('hidden');
}

function setError(message) {
    if (errorTimer) clearTimeout(errorTimer);
    setState({ error: message });
    errorTimer = setTimeout(() => setState({ error: null }), 5000);
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

    if (state.loading) {
        empty.classList.add('hidden');
        list.innerHTML = [1, 2, 3].map(() => skeletonCard()).join('');
        return;
    }

    if (state.habits.length === 0) {
        list.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');

    const periodData = await Promise.all(
        state.habits.map(h => habits.analytics(h.id).catch(() => []))
    );

    list.innerHTML = state.habits
        .map((habit, i) => habitCard(habit, periodData[i]))
        .join('');

    if (state.editingHabitId) {
        const input = document.querySelector(`.habit-task-input[data-id="${state.editingHabitId}"]`);
        if (input) input.focus();
    }
}

function skeletonCard() {
    return `
        <div class="habit-card">
            <div class="skeleton skeleton-line"></div>
            <div class="skeleton skeleton-line short"></div>
            <div class="skeleton-dots">${'<span class="skeleton skeleton-dot"></span>'.repeat(18)}</div>
            <div class="skeleton skeleton-line short"></div>
        </div>
    `;
}

function isActionInFlight(action, id) {
    return Boolean(state.inFlightActions[`${action}:${id}`]);
}

function habitCard(habit, periods = []) {
    const dots = periods.slice(0, 30).map(p => {
        const cls = p.status === 'COMPLETED' ? 'dot-completed'
            : p.status === 'FAILED' ? 'dot-failed'
                : 'dot-active';
        return `<span class="dot ${cls}" title="${p.key}"></span>`;
    }).join('');

    const doneBusy = isActionInFlight('done', habit.id);
    const archiveBusy = isActionInFlight('archive', habit.id);

    const isEditing = state.editingHabitId === habit.id;
    const taskMarkup = isEditing
        ? `<input class="habit-task-input" data-id="${habit.id}" value="${escapeHtml(state.editDraft || habit.task_specification)}">`
        : `<span class="habit-task">${escapeHtml(habit.task_specification)}</span>`;

    return `
        <div class="habit-card clickable" data-id="${habit.id}">
            <div class="habit-card-header">
                ${taskMarkup}
                <span class="habit-periodicity">${habit.periodicity}</span>
            </div>
            <div class="habit-dots">${dots}</div>
            <div class="habit-card-footer">
                <button class="btn-done" data-action="done" data-id="${habit.id}" ${doneBusy ? 'disabled' : ''}>${doneBusy ? 'Saving...' : '✓ Done'}</button>
                <button class="btn-archive" data-action="archive" data-id="${habit.id}" ${archiveBusy ? 'disabled' : ''}>${archiveBusy ? 'Archiving...' : 'Archive'}</button>
                <button class="btn-edit" data-action="edit" data-id="${habit.id}">${isEditing ? 'Editing...' : 'Edit'}</button>
            </div>
        </div>
    `;
}

function archivedCard(habit) {
    const unarchiveBusy = isActionInFlight('unarchive', habit.id);
    return `
        <div class="habit-card habit-card-archived" data-id="${habit.id}">
            <div class="habit-card-header">
                <span class="habit-task">${escapeHtml(habit.task_specification)}</span>
                <span class="habit-periodicity">${habit.periodicity}</span>
            </div>
            <div class="habit-card-footer">
                <button class="btn-unarchive" data-action="unarchive" data-id="${habit.id}" ${unarchiveBusy ? 'disabled' : ''}>${unarchiveBusy ? '...' : 'Unarchive'}</button>
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

function completionRateValue(habit) {
    if (habit.completion_rate === null || habit.completion_rate === undefined) return '—';
    const val = Number(habit.completion_rate);
    return Number.isFinite(val) ? `${val.toFixed(1)}%` : String(habit.completion_rate);
}

function renderDetailPanel() {
    const panel = document.getElementById('detail-panel');
    const content = document.getElementById('detail-panel-content');
    const selected = state.selectedHabit;

    if (!selected) {
        panel.classList.add('hidden');
        content.innerHTML = '';
        return;
    }

    panel.classList.remove('hidden');

    if (selected.loading) {
        content.innerHTML = '<p>Loading habit details...</p>';
        return;
    }

    const periods = (selected.periods || []).map(period => `
        <div class="detail-period-item">
            <span>${period.key}</span>
            <span>${period.status}</span>
        </div>
    `).join('') || '<p>No period history in this range.</p>';

    content.innerHTML = `
        <h4>${escapeHtml(selected.task_specification || '')}</h4>
        <p>${selected.periodicity}</p>

        <div class="detail-stats">
            <div class="detail-stat"><strong>${completionRateValue(selected)}</strong><br>rate</div>
            <div class="detail-stat"><strong>${selected.current_streak ?? 0}</strong><br>current</div>
            <div class="detail-stat"><strong>${selected.longest_streak ?? 0}</strong><br>longest</div>
        </div>

        <div class="detail-filter">
            <input id="detail-start" type="date" value="${selected.start || ''}">
            <input id="detail-end" type="date" value="${selected.end || ''}">
        </div>
        <div class="detail-filter-actions">
            <button class="btn-ghost" id="btn-apply-filter">Apply</button>
            <button class="btn-ghost" id="btn-clear-filter">Clear</button>
        </div>

        <div class="detail-period-list">${periods}</div>
    `;
}

async function init() {
    setState({ loading: true, error: null });
    try {
        const [me, summary, activeHabits, archivedHabits] = await Promise.all([
            auth.me(),
            analytics.summary(),
            habits.list({ is_archived: false }),
            habits.list({ is_archived: true }),
        ]);

        document.getElementById('header-username').textContent = me.username;

        setState({
            habits: activeHabits.results,
            archivedHabits: archivedHabits.results,
            summary,
        });
    } catch (err) {
        setError(err.message || 'Failed to load dashboard.');
    } finally {
        setState({ loading: false });
    }
}

function markAction(action, id, isLoading) {
    const key = `${action}:${id}`;
    const next = { ...state.inFlightActions };
    if (isLoading) next[key] = true;
    else delete next[key];
    setState({ inFlightActions: next });
}

async function handleComplete(id) {
    markAction('done', id, true);
    try {
        await completions.create(id);
        const updated = await habits.retrieve(id);
        setState({ habits: state.habits.map(h => h.id === id ? updated : h) });
        await refreshSummary();
    } catch (err) {
        setError(err.message || 'Failed to complete habit.');
    } finally {
        markAction('done', id, false);
    }
}

async function handleArchive(id) {
    markAction('archive', id, true);
    try {
        const updated = await habits.archive(id);
        setState({
            habits: state.habits.filter(h => h.id !== id),
            archivedHabits: [updated, ...state.archivedHabits],
        });
        await refreshSummary();
    } catch (err) {
        setError(err.message || 'Failed to archive habit.');
    } finally {
        markAction('archive', id, false);
    }
}

async function handleUnarchive(id) {
    markAction('unarchive', id, true);
    try {
        const updated = await habits.unarchive(id);
        setState({
            habits: [updated, ...state.habits],
            archivedHabits: state.archivedHabits.filter(h => h.id !== id),
        });
        await refreshSummary();
    } catch (err) {
        setError(err.message || 'Failed to unarchive habit.');
    } finally {
        markAction('unarchive', id, false);
    }
}

async function refreshSummary() {
    const summary = await analytics.summary();
    setState({ summary });
}

async function openDetail(id, start = '', end = '') {
    setState({ selectedHabit: { id, start, end, loading: true } });
    try {
        const [habit, periods] = await Promise.all([
            habits.retrieve(id),
            habits.analytics(id, start || null, end || null),
        ]);
        setState({ selectedHabit: { ...habit, periods, start, end, loading: false } });
    } catch (err) {
        setError(err.message || 'Failed to load detail panel.');
        setState({ selectedHabit: null });
    }
}

function startEdit(habitId) {
    const habit = state.habits.find(h => h.id === habitId);
    if (!habit) return;
    setState({ editingHabitId: habitId, editDraft: habit.task_specification });
}

async function saveInlineEdit(habitId) {
    if (state.editingHabitId !== habitId) return;
    const nextTask = (state.editDraft || '').trim();
    const oldHabit = state.habits.find(h => h.id === habitId);
    if (!oldHabit) return;

    if (!nextTask) {
        setError('Habit name cannot be empty.');
        setState({ editDraft: oldHabit.task_specification });
        return;
    }

    if (nextTask === oldHabit.task_specification) {
        setState({ editingHabitId: null, editDraft: '' });
        return;
    }

    try {
        const updated = await habits.update(habitId, nextTask);
        setState({
            habits: state.habits.map(h => h.id === habitId ? { ...h, task_specification: updated.task_specification } : h),
            selectedHabit: state.selectedHabit && state.selectedHabit.id === habitId
                ? { ...state.selectedHabit, task_specification: updated.task_specification }
                : state.selectedHabit,
            editingHabitId: null,
            editDraft: '',
        });
    } catch (err) {
        setError(err.message || 'Failed to rename habit.');
    }
}

function escapeHtml(text) {
    return String(text)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

document.getElementById('btn-logout').addEventListener('click', async () => {
    await auth.logout();
    window.location.href = '/login/';
});

document.getElementById('btn-export').addEventListener('click', () => analytics.export('csv'));
document.getElementById('btn-dismiss-error').addEventListener('click', () => setState({ error: null }));

document.getElementById('btn-add').addEventListener('click', () => {
    document.getElementById('modal-add').classList.remove('hidden');
});

document.getElementById('btn-modal-cancel').addEventListener('click', () => {
    document.getElementById('modal-add').classList.add('hidden');
    document.getElementById('modal-error').classList.add('hidden');
    document.getElementById('form-add-habit').reset();
});

document.getElementById('btn-close-detail').addEventListener('click', () => {
    setState({ selectedHabit: null });
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
        await refreshSummary();
    } catch (err) {
        document.getElementById('modal-error').textContent = err.message;
        document.getElementById('modal-error').classList.remove('hidden');
    }
});

document.getElementById('habit-list').addEventListener('input', (e) => {
    if (!e.target.classList.contains('habit-task-input')) return;
    setState({ editDraft: e.target.value });
});

document.getElementById('habit-list').addEventListener('keydown', async (e) => {
    if (!e.target.classList.contains('habit-task-input')) return;
    const id = e.target.dataset.id;
    if (e.key === 'Enter') {
        e.preventDefault();
        await saveInlineEdit(id);
    }
    if (e.key === 'Escape') {
        setState({ editingHabitId: null, editDraft: '' });
    }
});

document.getElementById('habit-list').addEventListener('focusout', async (e) => {
    if (!e.target.classList.contains('habit-task-input')) return;
    const id = e.target.dataset.id;
    await saveInlineEdit(id);
});

document.getElementById('habit-list').addEventListener('click', async (e) => {
    const actionBtn = e.target.closest('button[data-action]');
    const card = e.target.closest('.habit-card');
    const id = actionBtn?.dataset.id || card?.dataset.id;
    if (!id) return;

    if (actionBtn) {
        const action = actionBtn.dataset.action;
        if (action === 'done') await handleComplete(id);
        if (action === 'archive') await handleArchive(id);
        if (action === 'edit') startEdit(id);
        return;
    }

    if (e.target.classList.contains('habit-task-input')) return;
    await openDetail(id);
});

document.getElementById('btn-toggle-archived').addEventListener('click', () => {
    const list = document.getElementById('archived-list');
    const btn = document.getElementById('btn-toggle-archived');
    const isHidden = list.classList.toggle('hidden');
    btn.textContent = isHidden ? 'Show archived habits' : 'Hide archived habits';
});

document.getElementById('archived-list').addEventListener('click', async (e) => {
    const actionBtn = e.target.closest('button[data-action]');
    if (!actionBtn) return;
    const id = actionBtn.dataset.id;
    if (actionBtn.dataset.action === 'unarchive') {
        await handleUnarchive(id);
    }
});

document.getElementById('detail-panel').addEventListener('click', async (e) => {
    if (e.target.id === 'btn-apply-filter') {
        const selected = state.selectedHabit;
        if (!selected) return;
        const start = document.getElementById('detail-start').value;
        const end = document.getElementById('detail-end').value;
        await openDetail(selected.id, start, end);
    }
    if (e.target.id === 'btn-clear-filter') {
        const selected = state.selectedHabit;
        if (!selected) return;
        await openDetail(selected.id, '', '');
    }
});

init();
