class WordCollectionManager {
    constructor() {
        this.words = [];
        this.currentFilter = 'all';
        this.currentSortField = 'text';
        this.currentSortOrder = 'asc';
        this.currentPage = 1;
        this.pageSize = 20;
        this.totalPages = 1;
        this.totalItems = 0;
        
        // Initialize event listeners
        this.initializeEventListeners();
        
        // Load initial data
        this.loadWords();
    }
    
    initializeEventListeners() {
        // Filter buttons
        document.querySelectorAll('.filter-group .toggle-button').forEach(button => {
            button.addEventListener('click', () => {
                document.querySelectorAll('.filter-group .toggle-button').forEach(btn => {
                    btn.classList.remove('active');
                });
                button.classList.add('active');
                this.currentFilter = button.dataset.filter;
                this.currentPage = 1; // Reset to first page when filter changes
                this.loadWords();
            });
        });
        
        // Sort controls
        document.getElementById('sortField').addEventListener('change', (e) => {
            this.currentSortField = e.target.value;
            this.currentPage = 1; // Reset to first page when sort changes
            this.loadWords();
        });
        
        document.getElementById('sortOrder').addEventListener('change', (e) => {
            this.currentSortOrder = e.target.value;
            this.currentPage = 1; // Reset to first page when sort changes
            this.loadWords();
        });

        // Page size control
        document.getElementById('pageSize').addEventListener('change', (e) => {
            this.pageSize = parseInt(e.target.value);
            this.currentPage = 1; // Reset to first page when page size changes
            this.loadWords();
        });
    }
    
    async loadWords() {
        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                page_size: this.pageSize,
                sort_field: this.currentSortField,
                sort_order: this.currentSortOrder,
                filter: this.currentFilter
            });
            
            const response = await fetch(`/api/word_collections?${params.toString()}`);
            const data = await response.json();
            
            this.words = data.items;
            this.totalPages = data.pagination.total_pages;
            this.totalItems = data.pagination.total_items;
            this.renderWords();
        } catch (error) {
            console.error('Error loading words:', error);
            alert('Failed to load words. Please try again.');
        }
    }
    
    async toggleWordStatus(wordId) {
        try {
            const response = await fetch(`/api/word_collections/${wordId}/toggle`, {
                method: 'POST'
            });
            
            if (response.ok) {
                // Refresh the word list
                this.loadWords();
            } else {
                alert('Failed to update word status. Please try again.');
            }
        } catch (error) {
            console.error('Error toggling word status:', error);
            alert('Error updating word status. Please try again.');
        }
    }
    
    async deleteWord(wordId) {
        // if (!confirm(window.translations.delete_confirm || 'Are you sure you want to delete this word?')) {
        //     return;
        // }
        
        try {
            const response = await fetch(`/api/word_collections/${wordId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                // Refresh the word list
                this.loadWords();
            } else {
                const data = await response.json();
                alert(data.error || 'Failed to delete word. Please try again.');
            }
        } catch (error) {
            console.error('Error deleting word:', error);
            alert('Error deleting word. Please try again.');
        }
    }
    
    renderWords() {
        const tbody = document.getElementById('wordsTableBody');
        tbody.innerHTML = '';
        
        // Render words
        this.words.forEach(word => {
            const row = document.createElement('tr');
            if (word.is_removed) row.classList.add('removed');
            
            row.innerHTML = `
                <td>${word.text}</td>
                <td>${word.translation || ''}</td>
                <td>${word.context_text || ''}</td>
                <td>${new Date(word.collected_date).toLocaleDateString()}</td>
                <td>
                    <button onclick="wordManager.toggleWordStatus(${word.id})">
                        ${word.is_removed ? '🔄' : '✓'}
                    </button>
                    <button class="word-delete-button" onclick="wordManager.deleteWord(${word.id})">
                        🗑️
                    </button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
        
        // Update pagination controls
        const paginationControls = document.getElementById('paginationControls');
        paginationControls.innerHTML = '';
        
        const prevPageButton = document.createElement('button');
        prevPageButton.id = 'prevPage';
        prevPageButton.textContent = window.translations.previous;
        prevPageButton.disabled = this.currentPage === 1;
        prevPageButton.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.loadWords();
            }
        });
        paginationControls.appendChild(prevPageButton);
        
        const currentPageText = document.createElement('span');
        currentPageText.textContent = `${this.currentPage} / ${this.totalPages} (${this.totalItems})`;
        paginationControls.appendChild(currentPageText);
        
        const nextPageButton = document.createElement('button');
        nextPageButton.id = 'nextPage';
        nextPageButton.textContent = window.translations.next;
        nextPageButton.disabled = this.currentPage === this.totalPages;
        nextPageButton.addEventListener('click', () => {
            if (this.currentPage < this.totalPages) {
                this.currentPage++;
                this.loadWords();
            }
        });
        paginationControls.appendChild(nextPageButton);
    }
}

// Initialize the word manager
const wordManager = new WordCollectionManager();
