class ChannelManager {
    constructor(serverPort = 5001) {
        this.serverPort = serverPort;
        this.searchInput = document.getElementById('channel-search');
        this.searchButton = document.getElementById('search-button');
        this.favoriteToggle = document.getElementById('favorite-toggle');
        this.searchResults = document.getElementById('search-results');
        this.favoriteChannelsList = document.getElementById('favorite-channels-list');
        this.videosList = document.getElementById('videos-list');
        this.searchNotification = document.getElementById('search-notification');
        this.favoriteChannels = new Map();
        this.playedVideos = new Set(this.getPlayedVideos());        
        this.lastSearchResults = [];
        this.isInSearchMode = false;

        // Initialize pagination controls
        this.prevPageBtn = document.getElementById('prev-page');
        this.nextPageBtn = document.getElementById('next-page');
        this.currentPageSpan = document.getElementById('current-page');
        this.videosPerPageSelect = document.getElementById('videos-per-page');
        this.durationFilter = document.getElementById('duration-filter');

        // Language controls
        this.nativeLanguage = document.getElementById('native-language');
        this.subtitleLanguage = document.getElementById('subtitle-language');

        // Initialize state with defaults
        this.allVideos = [];
        this.filteredVideos = [];
        this.currentPage = 1;
        this.currentChannelId = null;

        // Default translations (fallback)
        this.translations = {
            // browserNotSupported: 'Your browser does not support the audio element.',
            // save: 'Save',
            // noChannelsFound: 'No channels found',
            // errorSearchingChannels: 'Error searching channels',
            // loadingAudios: 'Loading audios',
            // noVideosFound: 'No videos found',
            // saved: 'Saved',
            // saveFailed: 'Save failed'
        };

        // Try to get translations from window
        if (window.translations) {
            this.translations = { ...this.translations, ...window.translations };
        }

        // Load saved state
        const savedState = window.stateManager.loadPageState('channels');
        if (savedState) {
            console.log('Loaded state:', savedState);
            this.currentPage = savedState.currentPage || 1;
            this.currentChannelId = savedState.currentChannelId;
            this.allVideos = savedState.allVideos || [];
            this.filteredVideos = savedState.filteredVideos || [];
            this.lastSearchResults = savedState.lastSearchResults || [];
            this.isInSearchMode = savedState.isInSearchMode || false;
            
            if (savedState.searchQuery) {
                this.searchInput.value = savedState.searchQuery;
            }

            // First load favorite channels
            this.loadFavoriteChannels().then(() => {
                // Then apply the saved state to UI
                if (this.currentChannelId) {
                    if (this.isInSearchMode) {
                        // Show search results
                        this.searchResults.style.display = 'block';
                        this.favoriteChannelsList.style.display = 'none';
                        this.searchButton.classList.add('primary-button');
                        this.searchButton.classList.remove('secondary-button');
                        this.favoriteToggle.classList.add('secondary-button');
                        this.favoriteToggle.classList.remove('primary-button');
                        
                        // Restore search results and highlight selected channel
                        if (this.lastSearchResults.length > 0) {
                            this.renderSearchResults(this.lastSearchResults);
                            const channelElement = this.searchResults.querySelector(`[data-channel-id="${this.currentChannelId}"]`);
                            if (channelElement) {
                                channelElement.classList.add('active');
                            }
                        }
                    } else {
                        // Show favorites
                        this.searchResults.style.display = 'none';
                        this.favoriteChannelsList.style.display = 'block';
                        this.favoriteToggle.classList.add('primary-button');
                        this.favoriteToggle.classList.remove('secondary-button');
                        this.searchButton.classList.add('secondary-button');
                        this.searchButton.classList.remove('primary-button');
                        
                        // Highlight selected channel in favorites
                        const channelElement = this.favoriteChannelsList.querySelector(`[data-channel-id="${this.currentChannelId}"]`);
                        if (channelElement) {
                            channelElement.classList.add('active');
                        }
                    }
                    
                    // Update videos list and pagination
                    this.updateDisplayedVideos();
                    this.updatePaginationControls();
                }
            });
        } else {
            console.log('No saved state found');
            this.loadFavoriteChannels();
        }

        // Save state before user leaves page
        window.addEventListener('beforeunload', () => {
            const state = {
                currentPage: this.currentPage,
                currentChannelId: this.currentChannelId,
                allVideos: this.allVideos,
                filteredVideos: this.filteredVideos,
                searchQuery: this.searchInput.value,
                lastSearchResults: this.lastSearchResults,
                isInSearchMode: this.isInSearchMode
            };
            window.stateManager.savePageState('channels', state);
            console.log('Saved state:', state);
        });

        // Initialize event listeners
        this.searchButton.onclick = () => this.searchChannel();
        this.favoriteToggle.onclick = () => this.showFavorites();
        this.searchInput.onkeypress = (e) => {
            if (e.key === 'Enter') {
                this.searchChannel();
            }
        };

        // Pagination and filter event listeners
        this.prevPageBtn.onclick = () => this.changePage(this.currentPage - 1);
        this.nextPageBtn.onclick = () => this.changePage(this.currentPage + 1);
        this.videosPerPageSelect.onchange = () => this.updateDisplayedVideos();
        this.durationFilter.onchange = () => this.filterAndDisplayVideos();

        // Hide notification when user starts typing
        this.searchInput.oninput = () => {
            this.searchNotification.classList.add('hidden');
        };

        // Initialize auto-save settings
        this.autoSaveDuration = 3; // Default 3 minutes
        this.currentPlayTime = 0;
        this.autoSaveInitiated = false;
        
        // Load settings on initialization
        this.loadSettings();
        this.init();
    }

    async init() {
        await this.loadFavoriteChannels();
        this.showFavorites();
    }

    showFavorites() {
        this.isInSearchMode = false;
        // Show favorites list
        this.searchResults.style.display = 'none';
        this.favoriteChannelsList.style.display = 'block';
        this.searchNotification.classList.add('hidden');

        // Update button states
        this.favoriteToggle.classList.remove('secondary-button');
        this.favoriteToggle.classList.add('primary-button');
        this.searchButton.classList.add('secondary-button');
        this.searchButton.classList.remove('primary-button');
        // Clear search input
        this.searchInput.value = '';
    }

    async searchChannel() {
        this.isInSearchMode = true;
        this.searchButton.classList.add('primary-button');
        this.searchButton.classList.remove('secondary-button');
        this.favoriteToggle.classList.remove('primary-button');
        this.favoriteToggle.classList.add('secondary-button');

        const query = this.searchInput.value.trim();
        try {
            // Show search results
            this.searchResults.style.display = 'block';
            this.favoriteChannelsList.style.display = 'none';
            this.searchNotification.classList.add('hidden');

            var data = { success: "failed" }
            if (!query) {
                const response = await fetch(`http://localhost:${this.serverPort}/api/suggested-channels`);
                data = await response.json();
                
                // Get language preferences, fallback to 'en' if not set
                const subtitleLang = this.subtitleLanguage ? this.subtitleLanguage.value : 'en';

                console.log('subtitleLang:', subtitleLang);
                
                if (data.status === 'success' && data.channels && data.channels[subtitleLang]) {
                    this.renderSearchResults(data.channels[subtitleLang] || []);
                } else {
                    this.searchResults.innerHTML = `<div class="error">${this.translations.noChannelsFound}</div>`;
                }
            } else {
                this.searchResults.innerHTML = `<div class="loading">${this.translations.loadingChannels}</div>`;
                const response = await fetch(`http://localhost:${this.serverPort}/api/search-channel/${encodeURIComponent(query)}`);
                data = await response.json();
                if (data.status === 'success') {
                    this.renderSearchResults(data.channels || []);
                } else {
                    this.searchResults.innerHTML = `<div class="error">${this.translations.noChannelsFound}</div>`;
                }
            }
        } catch (error) {
            console.error('Error searching channel:', error);
            this.searchResults.innerHTML = `<div class="error">${this.translations.errorSearchingChannels}</div>`;
        }
    }

    async loadSuggestedChannels() {
        try {
            const response = await fetch(`http://localhost:${this.serverPort}/api/suggested-channels`);
            const data = await response.json();

            if (data.status === 'success') {
                this.favoriteChannels = new Map(
                    data.channels.map(c => [c.channel_name, c.channel_id])
                );
                this.renderSugggestedChannels();
            }
        } catch (error) {
            console.error('Error loading favorite channels:', error);
        }
    }

    async loadFavoriteChannels() {
        try {
            const response = await fetch(`http://localhost:${this.serverPort}/api/favorite-channels`);
            const data = await response.json();

            if (data.status === 'success') {
                this.favoriteChannels = new Map(
                    data.channels.map(c => [c.channel_name, c.channel_id])
                );
                this.renderFavoriteChannels();
            }
        } catch (error) {
            console.error('Error loading favorite channels:', error);
        }
    }

    async toggleFavorite(channelId, channelName) {
        try {
            const method = this.favoriteChannels.has(channelName) ? 'DELETE' : 'POST';
            const response = await fetch(`http://localhost:${this.serverPort}/api/favorite-channel/${channelId}`, {
                method,
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ channel_name: channelName })
            });

            const data = await response.json();
            if (data.status === 'success') {
                if (method === 'POST') {
                    this.favoriteChannels.set(channelName, channelId);
                } else {
                    this.favoriteChannels.delete(channelName);
                }
                this.renderSearchResults(this.lastSearchResults);
                this.renderFavoriteChannels();
            }
        } catch (error) {
            console.error('Error toggling favorite:', error);
        }
    }

    async loadChannelVideos(channelId) {
        this.currentChannelId = channelId;
        
        // Remove active class from all channel items
        document.querySelectorAll('.channel-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Add active class to clicked channel
        const clickedChannel = document.querySelector(`.channel-item[onclick*="${channelId}"]`);
        if (clickedChannel) {
            clickedChannel.classList.add('active');
        }

        this.videosList.innerHTML = '<div class="loading">' + this.translations.loadingAudios + '</div>';

        const response = await fetch(
            `http://localhost:${this.serverPort}/api/channel-videos/${channelId}`
        );
        const data = await response.json();
        console.log('Video data from server:', data.videos?.[0]); // Log first video for debugging

        if (data.status === 'success') {
            this.allVideos = data.videos;
            this.filteredVideos = this.allVideos;
            this.currentPage = 1;
            this.updateDisplayedVideos();
        } else {
            console.log("No videos found for channel:", channelId);
            this.videosList.innerHTML = '<div class="error">' + this.translations.noVideosFound + '</div>';
        }
    }

    filterAndDisplayVideos() {
        const duration = this.durationFilter.value;
        
        if (duration === 'all') {
            this.filteredVideos = this.allVideos;
        } else {
            this.filteredVideos = this.allVideos.filter(video => {
                if (!video.duration_seconds || isNaN(video.duration_seconds)) return false;
                
                switch (duration) {
                    case 'short':
                        return video.duration_seconds <= 600; // 0-10 minutes (600 seconds)
                    case 'medium':
                        return video.duration_seconds > 600 && video.duration_seconds <= 1800; // 10-30 minutes
                    case 'long':
                        return video.duration_seconds > 1800; // > 30 minutes
                    default:
                        return true;
                }
            });
        }
        
        this.currentPage = 1;
        this.updateDisplayedVideos();
    }

    async updateDisplayedVideos() {
        if (!this.filteredVideos || this.filteredVideos.length === 0) {
            this.videosList.innerHTML = '<div class="placeholder-text">' + this.translations.noVideosFound + '</div>';
            return;
        }

        const perPage = parseInt(this.videosPerPageSelect.value);
        const start = (this.currentPage - 1) * perPage;
        const end = start + perPage;
        const pageVideos = this.filteredVideos.slice(start, end);
        let savedVideos = new Set();
        try{
            const response = await fetch(`http://localhost:${this.serverPort}/api/check-saved-videos`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_ids: pageVideos.map(v => v.id)
                })
            });
            const data = await response.json();
            savedVideos = new Set(data.saved_videos);    
        }catch(error){
            console.error('Error checking saved videos:', error);
        }
            
        this.videosList.innerHTML = pageVideos.map(video => {
            // Extract duration from either duration or duration_string field
            const duration = this.formatDuration(video.duration_seconds);
            const isPlayed = this.playedVideos.has(video.id);
            
            return `
                <div class="video-item${isPlayed ? ' played' : ''}" data-video-id="${video.id}">
                    <div class="video-info">
                        <div class="video-title">${video.title}</div>
                        <div class="video-duration">${duration}</div>
                        <div class="audio-controls" style="display: none;">
                            <audio controls>
                                <source type="audio/mpeg">
                                ${this.translations.browserNotSupported}
                            </audio>
                        </div>
                    </div>
                 
                    <div class="video-actions">

                    ${savedVideos.has(video.id) 
                        ? `<button class="save-button saved" disabled>${this.translations.saved}</button>`
                        : `<button class="save-button" data-video-id="${video.id}" onclick="channelManager.saveVideo('${video.id}', this)">${this.translations.save}</button>`
                    }                           
                    </div>                
                </div>
            `;
        }).join('');

        this.updatePaginationControls(perPage);
    }

    changePage(newPage) {
        const perPage = parseInt(this.videosPerPageSelect.value);
        const totalPages = Math.ceil(this.filteredVideos.length / perPage);

        if (newPage >= 1 && newPage <= totalPages) {
            this.currentPage = newPage;
            this.updateDisplayedVideos();
        }
    }

    updatePaginationControls(perPage) {
        const totalPages = Math.ceil(this.filteredVideos.length / perPage);
        this.currentPageSpan.textContent = this.currentPage;
        this.prevPageBtn.disabled = this.currentPage <= 1;
        this.nextPageBtn.disabled = this.currentPage >= totalPages;
    }

    async saveVideo(videoId, button) {
        try {
            // Disable button and show loading state
            if(!button){
                button = document.querySelector(`.video-item[data-video-id="${videoId}"] .save-button`);
            }
            if(!button){
                showToast(window.translations.saveFailed, 'error');
                return;
            }

            button.disabled = true;
            button.textContent = this.translations.saving;

            const response = await fetch(`/api/save-video/${videoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: videoId
                })
            });

            const data = await response.json();

            if (data.status === 'success') {
                // Update button to show success
                button.textContent = this.translations.saved;
                button.disabled = true;
                button.classList.add('saved');
            } else {
                throw new Error(data.message || 'Failed to save video');
            }
        } catch (error) {
            console.error('Error saving video:', error);
            // Reset button and show error
            button.textContent = this.translations.saveFailed;
            button.classList.add('error');

            // Reset button after delay
            setTimeout(() => {
                button.textContent = this.translations.save;
                button.disabled = false;
                button.classList.remove('error');
            }, 2000);
        }
    }

    renderSearchResults(channels) {
        if (!channels || channels.length === 0) {
            this.searchResults.innerHTML = `<div class="error">${this.translations.noChannelsFound}</div>`;
            return;
        }

        this.lastSearchResults = channels; // Store for re-rendering

        this.searchResults.innerHTML = channels.map(channel => `
            <div class="channel-item" onclick="channelManager.loadChannelVideos('${channel.channel_id}')">
                <div class="channel-info">${channel.name}</div>
                <div class="channel-actions" onclick="event.stopPropagation()">
                    <button class="favorite-button ${this.favoriteChannels.has(channel.name) ? 'active' : ''}" 
                            onclick="channelManager.toggleFavorite('${channel.channel_id}', '${channel.name}')">
                        ★
                    </button>
                </div>
            </div>
        `).join('');
    }

    renderFavoriteChannels() {
        if (this.favoriteChannels.size === 0) {
            this.favoriteChannelsList.innerHTML = `<div class="placeholder-text">${this.translations.noFavoriteChannels}</div>`;
            return;
        }

        const favoriteChannelsArray = Array.from(this.favoriteChannels.entries()).map(([name, id]) => ({
            name: name,
            id: id
        }));

        this.favoriteChannelsList.innerHTML = favoriteChannelsArray.map(channel => `
            <div class="channel-item" onclick="channelManager.loadChannelVideos('${channel.id}')">
                <div class="channel-info">${channel.name}</div>
                <div class="channel-actions" onclick="event.stopPropagation()">
                    <button class="favorite-button active" onclick="channelManager.toggleFavorite('${channel.id}', '${channel.name}')">
                        ★
                    </button>
                </div>
            </div>
        `).join('');
    }

    async displayVideos(videos) {
        if (!videos || videos.length === 0) {
            this.videosList.innerHTML = `<p>${this.translations.noVideosFound}</p>`;
            return;
        }

        // Check which videos are already saved
        try {
            const response = await fetch(`http://localhost:${this.serverPort}/api/check-saved-videos`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_ids: videos.map(v => v.id)
                })
            });
            const data = await response.json();
            const savedVideos = new Set(data.saved_videos);

            this.videosList.innerHTML = videos.map(video => `
                <div class="video-item" data-video-id="${video.id}">
                    <div class="video-info">
                        <div class="video-title">${video.title}</div>
                        <div class="video-meta">
                            <span class="video-duration">${video.duration}</span>
                        </div>
                        <div class="audio-controls" style="display: none;">
                            <audio controls>
                                <source type="audio/mpeg">
                                ${this.translations.browserNotSupported}
                            </audio>
                        </div>
                    </div>
                    ${savedVideos.has(video.id) 
                        ? `<button class="save-button saved" disabled>${this.translations.saved}</button>`
                        : `<button class="save-button" data-video-id="${video.id}" onclick="channelManager.saveVideo('${video.id}', this)">${this.translations.save}</button>`
                    }
                </div>
            `).join('');
        } catch (error) {
            console.error('Error checking saved videos:', error);
            // Fallback to default display if check fails
            this.videosList.innerHTML = videos.map(video => `
                <div class="video-item" data-video-id="${video.id}">
                    <div class="video-info">
                        <div class="video-title">${video.title}</div>
                        <div class="video-meta">
                            <span class="video-duration">${video.duration}</span>
                            <span class="video-views">${video.views} views</span>
                        </div>
                        <div class="audio-controls" style="display: none;">
                            <audio controls>
                                <source type="audio/mpeg">
                                ${this.translations.browserNotSupported}
                            </audio>
                        </div>
                    </div>
                    <button class="save-button" onclick="channelManager.saveVideo('${video.id}', this)">${this.translations.save}</button>
                </div>
            `).join('');
        }
    }

    getPlayedVideos() {
        const played = localStorage.getItem('playedVideos');
        return played ? JSON.parse(played) : [];
    }

    markVideoAsPlayed(videoId) {
        const played = this.getPlayedVideos();
        if (!played.includes(videoId)) {
            played.push(videoId);
            localStorage.setItem('playedVideos', JSON.stringify(played));
            this.playedVideos = new Set(played);
            
            // Update UI if the video is currently displayed
            const videoElement = document.querySelector(`.video-item[data-video-id="${videoId}"]`);
            if (videoElement) {
                videoElement.classList.add('played');
            }
        }
    }

    formatDuration(seconds) {
        if (!seconds || isNaN(parseInt(seconds))) {
            return '--:--';
        }
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
        }
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            const settings = await response.json();            
            // Load auto-save duration
            this.autoSaveDuration = settings.auto_save_duration || 3;
            // document.getElementById('autoSaveDuration').value = this.autoSaveDuration;            
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    handleTimeUpdate(audioEl, videoId) {
        // console.log('Time update:', audioEl.currentTime, this.autoSaveDuration, this.autoSaveInitiated);
        if (!this.autoSaveDuration || this.autoSaveInitiated) return;
        
        this.currentPlayTime = audioEl.currentTime;
        const durationInSeconds = this.autoSaveDuration * 60;
        
        if (this.currentPlayTime >= durationInSeconds) {
            this.autoSaveInitiated = true;
            this.saveVideo(videoId, null);
        }
    }

    // previewVideo(videoId) {
    //     // ... existing preview code ...
        
    //     audioEl.addEventListener('play', startTrackingPlayTime);
    //     audioEl.addEventListener('pause', stopTrackingPlayTime);
    //     audioEl.addEventListener('ended', stopTrackingPlayTime);
    //     audioEl.ontimeupdate = () => this.handleTimeUpdate(audioEl, videoId);
    //     // audioEl.addEventListener('timeupdate', () => this.handleTimeUpdate(audioEl, videoId));
        
    //     // Reset auto-save state when starting a new video
    //     this.currentPlayTime = 0;
    //     this.autoSaveInitiated = false;
    // }
}

// Global audio player state
let currentPlayingItem = null;
let lastPlayTime = 0;
let playTimeInterval = null;

// Play time tracking functions
function startTrackingPlayTime() {
    lastPlayTime = Date.now();
    playTimeInterval = setInterval(updatePlayTime, 10000); // Update every 10 seconds
}

function stopTrackingPlayTime() {
    if (playTimeInterval) {
        clearInterval(playTimeInterval);
        updatePlayTime();
    }
}

function updatePlayTime() {
    const now = Date.now();
    const playedSeconds = Math.floor((now - lastPlayTime) / 1000);
    if (playedSeconds > 0) {
        fetch('/api/statistics/play-time', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ seconds: playedSeconds })
        });
        lastPlayTime = now;
    }
}

function stopCurrentAudio() {
    if (currentPlayingItem) {
        const audioEl = currentPlayingItem.querySelector('audio');
        const audioControls = currentPlayingItem.querySelector('.audio-controls');

        if (audioEl) {
            audioEl.pause();
            audioEl.currentTime = 0;
            audioEl.src = ''; // Clear source
            stopTrackingPlayTime(); // Stop tracking when audio is stopped
        }

        if (audioControls) {
            audioControls.style.display = 'none';
        }

        currentPlayingItem.classList.remove('playing', 'loading');
        currentPlayingItem = null;
    }
}

function previewVideo(videoId) {
    const videoItem = document.querySelector(`.video-item[data-video-id="${videoId}"]`);
    if (!videoItem) return;

    // Stop any currently playing audio
    stopCurrentAudio();

    // Show loading state
    videoItem.classList.add('loading');
    console.log('Starting preview for:', videoId);

    // Request the stream URL
    fetch(`/api/preview-video/${videoId}`, {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Stream ready:', data.stream_url);

                // Re-query the video item in case it was removed/modified
                const videoItem = document.querySelector(`[data-video-id="${videoId}"]`);
                if (!videoItem) {
                    console.error('Video item not found after fetch');
                    return;
                }

                // Get or create audio element
                const audioControls = videoItem.querySelector('.audio-controls');
                if (!audioControls) {
                    console.error('Audio controls not found');
                    return;
                }
                
                let audioEl = audioControls.querySelector('audio');

                if (data.needs_proxy) {
                    // If proxy is configured, stream through our server
                    audioEl.src = `/api/proxy-stream/${videoId}`;
                } else {
                    // If no proxy, stream directly
                    audioEl.src = data.stream_url;
                }
                audioEl.load(); // Reload the audio element to apply the new source

                // Add play time tracking event listeners
                audioEl.addEventListener('play', startTrackingPlayTime);
                audioEl.addEventListener('pause', stopTrackingPlayTime);
                audioEl.addEventListener('ended', stopTrackingPlayTime);
                audioEl.ontimeupdate = () => channelManager.handleTimeUpdate(audioEl, videoId);

                audioControls.style.display = 'block';
                audioEl.play();

                // Update UI state
                videoItem.classList.remove('loading');
                videoItem.classList.add('playing');
                currentPlayingItem = videoItem;
                
                // Mark video as played
                channelManager.markVideoAsPlayed(videoId);
            } else {
                console.error('Error getting stream URL:', data.message);
                videoItem.classList.remove('loading');
            }
        })
        .catch(error => {
            console.error('Error previewing video:', error);
            videoItem.classList.remove('loading');
        });
}

// Event delegation for video items
document.addEventListener('click', (event) => {
    const videoItem = event.target.closest('.video-item');
    if (videoItem && !event.target.closest('.save-button')) {
        const videoId = videoItem.dataset.videoId;
        if (videoId) {
            previewVideo(videoId);
        }
    }
});

// Add keyboard event listener for space key to toggle audio playback
document.addEventListener('keydown', function (event) {
    console.log('Key pressed:', event.code);
    if (event.code === 'Space') {
        console.log('Space key pressed');
        if (currentPlayingItem) {
            const audioEl = currentPlayingItem.querySelector('audio');
            if (audioEl) {
                console.log('Found current playing audio element');
                if (audioEl.paused) {
                    console.log('Playing audio');
                    audioEl.play();
                } else {
                    console.log('Pausing audio');
                    audioEl.pause();
                }
            } else {
                console.log('No audio element found in currentPlayingItem');
            }
            event.preventDefault();
            event.stopPropagation();
        } else {
            console.log('No audio element is currently playing');
        }
    }
});

// Initialize the channel manager
const channelManager = new ChannelManager(window.location.port);

// Proxy Configuration Functions
async function loadSettingConfig() {
    try {
        const response = await fetch('/api/settings');
        const config = await response.json();
        
        // Load proxy settings
        if (config.proxy) {
            const proxyParts = config.proxy.split('://');
            if (proxyParts.length === 2) {
                document.getElementById('proxyType').value = proxyParts[0];
                const hostParts = proxyParts[1].split('@');
                if (hostParts.length === 2) {
                    // Has authentication
                    const [auth, host] = hostParts;
                    const [username, password] = auth.split(':');
                    document.getElementById('proxyUsername').value = decodeURIComponent(username || '');
                    document.getElementById('proxyPassword').value = decodeURIComponent(password || '');
                    const [hostname, port] = host.split(':');
                    document.getElementById('proxyHost').value = hostname || '';
                    document.getElementById('proxyPort').value = port || '';
                } else {
                    // No authentication
                    const [hostname, port] = hostParts[0].split(':');
                    document.getElementById('proxyHost').value = hostname || '';
                    document.getElementById('proxyPort').value = port || '';
                }
            }
        }
        
        // Load language settings
        document.getElementById('native-language').value = config.native_language || 'en';
        document.getElementById('subtitle-language').value = config.subtitle_language || 'en';
        
        // Load LLM API keys
        // document.getElementById('openai-key').value = config.openai_key || '';
        document.getElementById('hunyuan-key').value = config.hunyuan_key || '';
        document.getElementById('alibaba-key').value = config.alibaba_key || '';
        document.getElementById('default-llm').value = config.default_llm || 'none';
        document.getElementById('autoSaveDuration').value = config.auto_save_duration || 3;        
        
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

async function saveProxyConfig() {
    try {

        const default_llm = document.getElementById('default-llm').value;
        if (default_llm != 'none' && !document.getElementById(default_llm + '-key').value) {
            showToast(window.translations.apiKeyMissing, 'error');
            return;
        }

        // Build proxy URL from components
        let proxyUrl = '';
        const proxyHost = document.getElementById('proxyHost').value;
        const proxyPort = document.getElementById('proxyPort').value;
        const proxyType = document.getElementById('proxyType').value;
        const proxyUsername = document.getElementById('proxyUsername').value;
        const proxyPassword = document.getElementById('proxyPassword').value;

        if (proxyHost && proxyPort) {
            proxyUrl = `${proxyType}://`;
            if (proxyUsername && proxyPassword) {
                proxyUrl += `${encodeURIComponent(proxyUsername)}:${encodeURIComponent(proxyPassword)}@`;
            }
            proxyUrl += `${proxyHost}:${proxyPort}`;
        }

        const config = {
            proxy: proxyUrl,
            native_language: document.getElementById('native-language').value,
            subtitle_language: document.getElementById('subtitle-language').value,
            openai_key: document.getElementById('openai-key').value,
            hunyuan_key: document.getElementById('hunyuan-key').value,
            alibaba_key: document.getElementById('alibaba-key').value,
            default_llm: document.getElementById('default-llm').value,
            auto_save_duration: document.getElementById('autoSaveDuration').value
        };

        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(config)
        });

        if (response.ok) {
            // Update language if changed
            const currentLang = document.documentElement.lang;
            if (currentLang !== config.native_language) {
                const langResponse = await fetch(`/set-language/${config.native_language}`);
                if (langResponse.ok) {
                    // Reload page to apply new language
                    window.location.reload();
                    return;
                }
            }
            closeSettingDialog();
        } else {
            console.error('Failed to save settings');
        }
    } catch (error) {
        console.error('Error saving settings:', error);
    }
}

function switchTab(tabId) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Remove active class from all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabId);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Add active class to selected tab button
    const selectedButton = document.querySelector(`[onclick="switchTab('${tabId}')"]`);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
}

async function showSettingDialog() {
    await loadSettingConfig(); 
    document.getElementById('settingDialog').style.display = 'block';
    // Set initial active tab after a small delay to ensure dialog is visible
    setTimeout(() => {
        switchTab('proxy-tab');
    }, 100);
}

function closeSettingDialog() {
    
    document.getElementById('settingDialog').style.display = 'none';
}

// Close dialog when clicking outside
window.onclick = function (event) {
    const dialog = document.getElementById('settingDialog');
    if (event.target === dialog) {
        closeSettingDialog();
    }
}

// Initialize settings when page loads
document.addEventListener('DOMContentLoaded', async function () {

    loadSettingConfig();    
});


// Close dialog when clicking outside
window.addEventListener('click', function (event) {
    const dialog = document.getElementById('settingDialog');
    if (event.target === dialog) {
        dialog.style.display = 'none';
    }
});
