class StateManager {
    constructor() {
        this.storage = window.localStorage;
        this.memoryState = {};
    }

    // Save state before leaving page
    savePageState(pageName, state) {
        const pageState = {
            data: state,
            timestamp: new Date().getTime()
        };
        this.storage.setItem(`pageState_${pageName}`, JSON.stringify(pageState));
    }

    // Load state when entering page
    loadPageState(pageName) {
        const stateStr = this.storage.getItem(`pageState_${pageName}`);
        if (!stateStr) return null;
        
        const state = JSON.parse(stateStr);
        // Optional: Check if state is still valid (e.g., not too old)
        const now = new Date().getTime();
        const maxAge = 30 * 60 * 1000; // 30 minutes
        
        if (now - state.timestamp > maxAge) {
            this.storage.removeItem(`pageState_${pageName}`);
            return null;
        }
        
        return state.data;
    }

    // Save specific data that should persist across sessions
    setPersistentData(key, value) {
        this.storage.setItem(`persistent_${key}`, JSON.stringify({
            data: value,
            timestamp: new Date().getTime()
        }));
    }

    // Get persistent data
    getPersistentData(key) {
        const data = this.storage.getItem(`persistent_${key}`);
        return data ? JSON.parse(data).data : null;
    }

    // Set temporary state that should only last for current session
    setSessionState(key, value) {
        this.memoryState[key] = value;
    }

    // Get temporary state
    getSessionState(key) {
        return this.memoryState[key];
    }

    // Clear all temporary states
    clearSessionState() {
        this.memoryState = {};
    }

    // Clear old states (can be called periodically)
    clearOldStates() {
        const now = new Date().getTime();
        const maxAge = 24 * 60 * 60 * 1000; // 24 hours

        Object.keys(this.storage).forEach(key => {
            if (key.startsWith('pageState_') || key.startsWith('persistent_')) {
                const value = JSON.parse(this.storage.getItem(key));
                if (now - value.timestamp > maxAge) {
                    this.storage.removeItem(key);
                }
            }
        });
    }
}

// Create a global instance
window.stateManager = new StateManager();
