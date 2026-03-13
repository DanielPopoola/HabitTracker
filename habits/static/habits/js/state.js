const state = {
    habits: [],
    archivedHabits: [],
    summary: {},
    loading: false,
    error: null,
    selectedHabit: null,
    inFlightActions: {},
    editingHabitId: null,
    editDraft: '',
};

function setState(partial) {
    Object.assign(state, partial);
    render();
}
