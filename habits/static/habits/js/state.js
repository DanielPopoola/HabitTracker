const state = {
    habits: [],
    archivedHabits: [], 
    summary: {},
    loading: false,
    error: null,
    selectedHabit: null,
};

function setState(partial) {
    Object.assign(state, partial);
    render();  // render() is async but we don't await it here intentionally
}