class AudioTubePlayer {
    constructor() {
        this.audioPlayer = document.getElementById('audio-player');
        this.videoList = document.getElementById('video-list');
        this.transcript = document.getElementById('transcript');
        this.playbackSpeedButton = document.getElementById('playback-speed');
        
        // Segment controls
        this.prevButton = document.getElementById('prev-segment');
        this.nextButton = document.getElementById('next-segment');
        this.replayButton = document.getElementById('replay-segment');
        this.playButton = document.getElementById('play-button');
        this.allSegmentsButton = document.getElementById('all-segments');
        this.markedSegmentsButton = document.getElementById('marked-segments');
        this.summaryButton = document.getElementById('summary-button');
        this.summaryContainer = document.getElementById('summary-container');
        this.summaryContent = document.getElementById('summary-content');
        this.toastContainer = document.querySelector('.toast-container');
        
        this.currentVideoId = null;
        this.currentTranscript = null;
        this.markedSegments = [];  // Array of marked segments
        this.currentSegmentIndex = -1;
        this.playingMarkedOnly = false;
        this.serverPort = window.location.port;
        this.gapBetweenSegments = 2; // Gap in seconds between marked segments
        
        // Initialize played videos set
        this.playedVideos = new Set(this.getPlayedVideos());

        // Load saved state
        const savedState = window.stateManager?.loadPageState('player') || {};
        if (savedState.currentVideoId) {
            this.currentVideoId = savedState.currentVideoId;
            this.loadVideo(this.currentVideoId);
        }

        // Save state before user leaves page
        window.addEventListener('beforeunload', () => {
            window.stateManager?.savePageState('player', {
                currentVideoId: this.currentVideoId
            });
        });

        // Pagination controls
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.totalPages = 1;
        
        // Initialize controls
        this.playbackSpeedButton.onclick = () => this.togglePlaybackSpeed();
        this.prevButton.onclick = () => this.previousSegment();
        this.nextButton.onclick = () => this.nextSegment();
        this.replayButton.onclick = () => this.replaySegment();
        this.playButton.onclick = () => this.togglePlay();
        this.allSegmentsButton.onclick = () => this.switchMode(false);
        this.markedSegmentsButton.onclick = () => this.switchMode(true);
        this.summaryButton.onclick = () => this.handleSummaryRequest();
        
        // Add audio player event listeners
        this.audioPlayer.ontimeupdate = () => this.handleTimeUpdate();
        this.audioPlayer.onplay = () => this.handleAudioPlay();
        this.audioPlayer.onpause = () => this.handleAudioPause();
        
        // Track play time
        let lastPlayTime = 0;
        let playTimeInterval = null;

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

        // Add to audio event listeners
        this.audioPlayer.addEventListener('play', startTrackingPlayTime);
        this.audioPlayer.addEventListener('pause', stopTrackingPlayTime);
        this.audioPlayer.addEventListener('ended', stopTrackingPlayTime);
        
        this.translationDialog = document.getElementById('translationDialog');
        this.selectedTextSpan = document.getElementById('selectedText');
        this.translationTextSpan = document.getElementById('translationText');
        this.saveWordButton = document.getElementById('saveWord');
        this.isHandlingSelection = false; // Add flag for selection handling
        
        // Close button for translation dialog
        const closeBtn = this.translationDialog.querySelector('.close');
        closeBtn.onclick = () => this.clearTranslationDialog();
        
        // Close dialog when clicking outside
        window.onclick = (event) => {
            if (event.target === this.translationDialog) {
                this.clearTranslationDialog();
            }
        };
        
        // Save word button handler
        this.saveWordButton.onclick = () => this.saveSelectedWord();
        
        // Handle window resize
        window.addEventListener('resize', () => this.handleResize());
        // Initial size adjustment
        this.handleResize();

        this.init();
    }

    showToast(message, type = 'info', duration = 3000) {
        showToast(message, type, duration);
    }

    removeToast(toast) {
        toast.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => {
            if (toast.parentNode === this.toastContainer) {
                this.toastContainer.removeChild(toast);
            }
        }, 300);
    }

    handleResize() {
        const contentContainer = document.querySelector('.content-container');
        const transcriptContainer = document.querySelector('#transcript-container');        
        if (contentContainer && transcriptContainer) {
            // Get the viewport height
            const vh = window.innerHeight;
            // Get the content container's offset from the top of the page
            const containerOffset = contentContainer.getBoundingClientRect().height;
            // Calculate and set the height (subtract some padding)
            const newHeight = containerOffset - 20;
            // contentContainer.style.height = `${newHeight}px`;
            transcriptContainer.style.height = `${newHeight}px`;
            const summaryContainer = document.querySelector('#summary-container');      
            if(summaryContainer){
                summaryContainer.style.height = `${newHeight}px`;
            }    
        }
    }

    async init() {
        await this.loadVideoList();
    }

    async loadVideoList(page = 1) {
        try {
            const response = await fetch(`/api/videos?page=${page}&per_page=${this.itemsPerPage}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                this.renderVideoList(data.videos);
                this.totalPages = Math.ceil(data.total / this.itemsPerPage);
                this.currentPage = page;
                this.updatePaginationControls();
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Error loading video list:', error);
            this.videoList.innerHTML = 'Error loading videos: ' + error.message;
        }
    }

    updatePaginationControls() {
        const paginationHtml = `
            <div class="pagination">
                <button ${this.currentPage <= 1 ? 'disabled' : ''} onclick="player.loadVideoList(${this.currentPage - 1})">${window.translations.Previous}</button>
                <span>${this.currentPage} / ${this.totalPages}</span>
                <button ${this.currentPage >= this.totalPages ? 'disabled' : ''} onclick="player.loadVideoList(${this.currentPage + 1})">${window.translations.Next}</button>
            </div>
        `;
        
        // Add pagination controls after video list
        let paginationDiv = document.querySelector('.pagination');
        if (!paginationDiv) {
            paginationDiv = document.createElement('div');
            this.videoList.parentNode.insertBefore(paginationDiv, this.videoList.nextSibling);
        }
        paginationDiv.outerHTML = paginationHtml;
    }

    renderVideoList(videos) {
        this.videoList.innerHTML = '';
        videos.forEach(video => {
            const videoItem = document.createElement('div');
            videoItem.className = 'video-item';
            if (this.playedVideos.has(video.video_id)) {
                videoItem.classList.add('played');
            }
            videoItem.dataset.videoId = video.video_id;
            videoItem.innerHTML = `
                <div class="video-info">
                    <div class="video-title">${video.title}</div>
                    <div class="video-channel">${video.channel_name}</div>
                    <div class="video-duration-date">
                        <div class="video-date">${new Date(video.created_at).toLocaleDateString()}</div>
                        <div class="video-duration">${this.formatDuration(video.duration)}</div>                                            
                    </div>
                </div>
                <button class="delete-button" title="${window.translations.delete}" aria-label="${window.translations.delete}" data-video-id="${video.video_id}">
                    <i class="fas fa-trash"></i></button>
            `;
            
            videoItem.querySelector('.video-info').onclick = () => {
                // Remove active class from all video items
                document.querySelectorAll('.video-item').forEach(item => {
                    item.classList.remove('active');
                });
                // Add active class to clicked item
                videoItem.classList.add('active');
                this.loadVideo(video.video_id);
            };
            videoItem.querySelector('.delete-button').onclick = (e) => {
                e.stopPropagation();
                this.deleteVideo(video.video_id);
            };
            
            this.videoList.appendChild(videoItem);
        });
    }

    async loadVideo(videoId) {
        this.currentTranscript = null;
        this.markedSegments = null;
        this.currentVideoId = videoId;
        this.showSummary("");        
        try {
            const response = await fetch(`/api/video/${videoId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // Add end time for each segment
                this.currentTranscript = data.transcript.map((segment, index, array) => ({
                    ...segment,
                    end: index < array.length - 1 ? array[index + 1].start : segment.start + 30
                }));                
                // Update audio source
                this.audioPlayer.src = `/api/audio/${videoId}`;                
                
                // Load marked segments
                await this.loadMarkedSegments(videoId);
                
                // Render transcript
                this.renderTranscript();
                this.switchMode(false);                
                // Update active video in list
                document.querySelectorAll('.video-item').forEach(item => {
                    item.classList.toggle('active', item.querySelector('.delete-button').dataset.videoId === videoId);
                });
                this.markVideoAsPlayed(videoId);
                this.handleSummaryRequest();
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Error loading video:', error);
        }
    }

    async loadMarkedSegments(videoId) {
        try {
            const response = await fetch(`/api/marked-segments/${videoId}`);
            const data = await response.json();
            
            if (data.status === 'success') {
                // Store complete marked segment objects
                this.markedSegments = data.segments;
            }
        } catch (error) {
            console.error('Error loading marked segments:', error);
        }
    }

    async markSegment(start, text) {
        try {
            const response = await fetch(`/api/mark-segment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: this.currentVideoId,
                    segment_start: start,
                    segment_text: text
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                this.markedSegments.push({ start, text });
                this.updateSegmentUI(start);
            }
        } catch (error) {
            console.error('Error marking segment:', error);
        }
    }

    async unmarkSegment(start) {
        try {
            const response = await fetch(`/api/unmark-segment`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    video_id: this.currentVideoId,
                    segment_start: start
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                this.markedSegments = this.markedSegments.filter(segment => segment.start !== start);
                this.updateSegmentUI(start);
            }
        } catch (error) {
            console.error('Error unmarking segment:', error);
        }
    }

    updateSegmentUI(start) {
        const segments = document.querySelectorAll('.transcript-segment');
        segments.forEach(segment => {
            if (parseFloat(segment.dataset.start) === start) {
                segment.classList.toggle('marked', this.markedSegments.some(s => s.start === start));
            }
        });
    }

    async deleteVideo(videoId) {
        if (!confirm('Are you sure you want to delete this video?')) {
            return;
        }

        try {
            const response = await fetch(`/api/video/${videoId}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.status === 'success') {
                if (this.currentVideoId === videoId) {
                    this.currentVideoId = null;
                    this.currentTranscript = null;
                    this.audioPlayer.src = '';
                    this.transcript.innerHTML = '';
                }
                await this.loadVideoList(this.currentPage);
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('Error deleting video:', error);
        }
    }

    renderTranscript() {
        if (!this.currentTranscript) {
            this.transcript.innerHTML = '';
            return;
        }

        this.transcript.innerHTML = this.currentTranscript.map((segment, index) => `
            <div class="transcript-segment ${this.markedSegments.some(s => s.start === segment.start) ? 'marked' : ''}" 
                 data-index="${index}" 
                 data-start="${segment.start}"
                 data-end="${segment.end}">
                <span class="timestamp">${this.formatTime(segment.start)}</span>
                <span class="text">${segment.text}</span>
                <button class="mark-button">
                    ${this.markedSegments.some(s => s.start === segment.start) ? '★' : '☆'}
                </button>
            </div>
        `).join('');

        // Add click handlers to segments
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            let isTextSelected = false;
            let clickTimeout;

            segment.onmousedown = () => {
                isTextSelected = false; // Reset selection flag
            };

            segment.onmouseup = () => {
                isTextSelected = window.getSelection().toString().length > 0;
            };

            segment.onclick = (e) => {
                if (e.detail === 1) {
                    // Delay the single click action to see if it's part of a double click
                    clickTimeout = setTimeout(() => {
                        if (isTextSelected) {
                            return;
                        }

                        if (e.target.classList.contains('mark-button')) {
                            const start = parseFloat(segment.dataset.start);
                            const text = segment.querySelector('.text').textContent;
                            if (this.markedSegments.some(s => s.start === start)) {
                                this.unmarkSegment(start);
                            } else {
                                this.markSegment(start, text);
                            }
                        } else {
                            const start = parseFloat(segment.dataset.start);
                            this.audioPlayer.currentTime = start;
                            this.audioPlayer.play();
                        }
                    }, 200); // 200ms delay to wait for potential double click
                }
            };

            segment.ondblclick = (e) => {
                clearTimeout(clickTimeout); // Cancel the single click action
            };
        });
        
        // Add mouseup event listener to handle text selection
        document.addEventListener('mouseup', (event) => {
            this.handleTextSelection(event);
        });
    }

    async handleTextSelection(event) {
        // If already handling a selection, skip
        if (this.isHandlingSelection) return;
        
        const selection = window.getSelection();
        const selectedText = selection.toString().trim();
        
        if (!selectedText) return;
        
        // Check if selection is within a span with class 'text'
        const textSpan = selection.anchorNode.parentElement.closest('span.text');
        if (!textSpan) return;
        
        // Set flag before starting translation
        this.isHandlingSelection = true;
        
        // Get context from the text span
        const contextText = textSpan.textContent || '';
        
        try {
            // Get user's language setting
            const response = await fetch('/api/settings');
            const settings = await response.json();
            if (settings.default_llm == 'none') {
                return;
            }
            const targetLanguage = settings.native_language || 'en';

            var translation = null;

            if (!settings.default_llm || !settings[settings.default_llm + "_key"]){
                this.showToast(window.translations.aipKeyMissing, 'error');
                return;
            }else{
                let endPoint = "";
                let model = "";
                let apiKey = settings[settings.default_llm + "_key"];
                if (settings.default_llm == "openai") {
                    console.log("try to get translation with openai");
                    endPoint = "https://api.openai.com/v1/chat/completions";
                    model = "gpt-3.5-turbo";
                    translation = await this.translateSentence(endPoint, model, apiKey, contextText, selectedText, targetLanguage);
                }else if(settings.default_llm == "alibaba"){
                    console.log("try to get translation with alibaba");
                    endPoint = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions";
                    model = "qwen-plus";                   
                    translation = await this.translateSentence(endPoint, model, apiKey, contextText, selectedText, targetLanguage);
                }else if(settings.default_llm == "hunyuan"){
                    console.log("try to get translation with huanyuan");
                    endPoint = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions";
                    model = "hunyuan-turbo";
                    translation = await this.translateSentence(endPoint, model, apiKey, contextText, selectedText, targetLanguage);
                }else{
                    console.log("unknown llm", settings.default_llm, settings.default_llm + "_key", settings[settings.default_llm + "_key"] );
                    window.getSelection().removeAllRanges();
                    return;
                }
            }
                    
            if (translation) {
                window.getSelection().removeAllRanges();          

                // Show translation dialog
                this.selectedTextSpan.textContent = selectedText;
                this.translationTextSpan.textContent = translation;
                this.translationDialog.style.display = 'block';
                
                // Store current segment info for saving
                this.currentSelection = {
                    text: selectedText,
                    translation: translation,
                    audioPath: this.audioPlayer.src,
                    segmentStart: this.currentTranscript && 
                                this.currentSegmentIndex >= 0 && 
                                this.currentTranscript[this.currentSegmentIndex] ? 
                                this.currentTranscript[this.currentSegmentIndex].start : 0,
                    segmentEnd: this.currentTranscript && 
                               this.currentSegmentIndex >= 0 && 
                               this.currentTranscript[this.currentSegmentIndex] ? 
                               this.currentTranscript[this.currentSegmentIndex].end : 0,
                    contextText: contextText
                };
            }
        } catch (error) {
            console.error('Translation error:', error);
            // Clear selection before showing alert
            window.getSelection().removeAllRanges();
            this.showToast(window.translations.translateFailed, 'error');
        } finally {
            // Clear the flag after handling is complete
            window.getSelection().removeAllRanges();
            this.isHandlingSelection = false;
        }
    }

    async saveSelectedWord() {
        if (!this.currentSelection) return;
        
        try {
            const response = await fetch('/api/word_collections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    selected_text: this.currentSelection.text,
                    translation: this.currentSelection.translation,
                    audio_path: this.currentSelection.audioPath,
                    segment_start: this.currentSelection.segmentStart,
                    segment_end: this.currentSelection.segmentEnd,
                    context_text: this.currentSelection.contextText,
                    collected_date: dayjs().format('YYYY-MM-DD')
                })
            });
            
            if (response.ok) {
                this.showToast(window.translations.wordSaved, 'success');
                this.clearTranslationDialog();
            } else {
                this.showToast(window.translations.wordSaveFailed, 'error');
            }
        } catch (error) {
            console.error('Error saving word:', error);
            this.showToast(window.translations.wordSaveFailed, 'error');
        }
    }

    clearTranslationDialog() {
        this.translationDialog.style.display = 'none';
        this.currentSelection = null;
        this.isHandlingSelection = false;
        // Clear the text selection
        window.getSelection().removeAllRanges();
    }

    async translateSentence(endPoint,  model, apiKey, context_text, selectedText, target_language) {
        try {
            const response = await axios.post(
                endPoint,
                {
                    model: model,
                    messages: [
                        {
                            role: "system",
                            content: "You are a translator."
                        },
                        {
                            role: "user",
                            content: `Give me the ${target_language} translation of '${selectedText}' in the context of '${context_text}', and just give me the translation as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Hunyuan:', error);
            return '';
        }       
    }

    async translateSentenceWithOpenAI(apiKey,context_text, selectedText, target_language) {
        try {
            const response = await axios.post(
                'https://api.openai.com/v1/chat/completions',
                {
                    model: "gpt-3.5-turbo",
                    messages: [
                        {
                            role: "system",
                            content: "You are a translator."
                        },
                        {
                            role: "user",
                            content: `Give me the ${target_language} translation of '${selectedText}' in the context of '${context_text}', and just give me the translation as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Hunyuan:', error);
            return '';
        }
    }

    async translateSentenceWithHunyuan(apiKey, context_text, selectedText, target_language) {
        try {
            const response = await axios.post(
                '/api/translate/hunyuan',
                {
                    model: "hunyuan-turbo",
                    messages: [
                        {
                            role: "system",
                            content: "You are a translator."
                        },
                        {
                            role: "user",
                            content: `Give me the ${target_language} translation of '${selectedText}' in the context of '${context_text}', and just give me the translation as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Hunyuan:', error);
            return '';
        }
    }

    

    async translateSentenceWithAli(apiKey, context_text, selectedText, target_language) {
        try {
            const response = await axios.post(
                'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                {
                    model: "qwen-plus",
                    messages: [
                        {
                            role: "system",
                            content: "You are a translator."
                        },
                        {
                            role: "user",
                            content: `Give me the ${target_language} translation of '${selectedText}' in the context of '${context_text}', and just give me the translation as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Ali:', error);
            return '';
        }
    }

    handleTimeUpdate() {        
        const currentTime = this.audioPlayer.currentTime;
        const segments = this.playingMarkedOnly ? this.markedSegments : this.currentTranscript;
        
        if (!segments || segments.length === 0) {
            return;
        }

        // Find the current segment based on time if not in marked mode
        if (!this.playingMarkedOnly) {
            for (let i = 0; i < segments.length; i++) {
                const segment = segments[i];
                if (currentTime >= segment.start && currentTime < segment.end) {
                    if (this.currentSegmentIndex !== i) {
                        this.currentSegmentIndex = i;                        
                    }
                    this.updateActiveSegment(true);
                    return;
                }
            }
        } else {
            // For marked segments mode
            if (this.currentSegmentIndex === -1 || this.currentSegmentIndex >= segments.length) {
                // Try to find the current segment based on time
                for (let i = 0; i < segments.length; i++) {
                    const segment = segments[i];
                    if (currentTime >= segment.start && currentTime < segment.end) {
                        this.currentSegmentIndex = i;
                        this.updateActiveSegment(true);                        
                        return;
                    }
                }
            } else {
                const currentSegment = segments[this.currentSegmentIndex];
                if (currentTime >= currentSegment.end) {
                    const nextIndex = this.currentSegmentIndex + 1;
                    if (nextIndex < segments.length) {
                        this.audioPlayer.pause();
                        setTimeout(() => {
                            this.playSegment(nextIndex);
                        }, this.gapBetweenSegments * 1000);
                    } else {
                        this.currentSegmentIndex = -1;
                    }
                    this.updateActiveSegment(true);
                }
            }
        }
    }

    updateActiveSegment(shouldScroll) {
        // Update visibility based on mode
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            const start = parseFloat(segment.dataset.start);
            const isMarked = this.markedSegments.some(s => s.start === start);
            
            if (this.playingMarkedOnly) {
                segment.style.display = isMarked ? 'flex' : 'none';
            } else {
                segment.style.display = 'flex';
            }
            
            // Remove active class from all segments
            segment.classList.remove('active');
        });

        // Add active class to current segment
        if (this.currentSegmentIndex !== -1) {
            const segments = this.playingMarkedOnly ? this.markedSegments : this.currentTranscript;
            const currentSegmentStart = segments[this.currentSegmentIndex].start;
            const activeSegment = document.querySelector(`.transcript-segment[data-start="${currentSegmentStart}"]`);
            if (activeSegment) {
                activeSegment.classList.add('active');
                
                // Scroll into view if needed
                // if (shouldScroll && !activeSegment.classList.contains('scrolled')) {
                    activeSegment.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    // activeSegment.classList.add('scrolled');
                // }
            }
        }
    }

    togglePlaybackSpeed() {
        const speeds = [1, 1.5, 2, 0.5];
        const currentSpeed = this.audioPlayer.playbackRate;
        const currentIndex = speeds.indexOf(currentSpeed);
        const nextIndex = (currentIndex + 1) % speeds.length;
        
        this.audioPlayer.playbackRate = speeds[nextIndex];
        this.playbackSpeedButton.textContent = `${speeds[nextIndex]}x`;
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        const parts = [];
        if (hours > 0) {
            parts.push(String(hours).padStart(2, '0'));
        }
        parts.push(String(minutes).padStart(2, '0'));
        parts.push(String(remainingSeconds).padStart(2, '0'));
        
        return parts.join(':');
    }

    switchMode(markedOnly) {
        this.playingMarkedOnly = markedOnly;
        this.allSegmentsButton.classList.toggle('active', !markedOnly);
        this.markedSegmentsButton.classList.toggle('active', markedOnly);
        
        // Stop playback and reset position
        this.audioPlayer.pause();
        this.currentSegmentIndex = -1;
        
        // Set initial position based on mode
        const segments = markedOnly ? this.markedSegments : this.currentTranscript;
        if (segments && segments.length > 0) {
            this.audioPlayer.currentTime = segments[0].start;
        }
        
        this.updateControlState();
        this.updateSegmentVisibility();
    }

    updateSegmentVisibility() {
        document.querySelectorAll('.transcript-segment').forEach(segment => {
            const start = parseFloat(segment.dataset.start);
            const isMarked = this.markedSegments.some(s => s.start === start);
            segment.style.display = this.playingMarkedOnly && !isMarked ? 'none' : 'flex';
        });
    }

    playSegment(index) {
        // console.log('Playing segment:', index);
        // console.log('Playing mode:', this.playingMarkedOnly);
        
        const segments = this.playingMarkedOnly ? this.markedSegments : this.currentTranscript;
        
        if (index >= 0 && index < segments.length) {
            const segment = segments[index];
            console.log('Playing segment:', segment);
            
            this.audioPlayer.currentTime = segment.start;
            this.audioPlayer.play();
            this.currentSegmentIndex = index;
            this.updateControlState();
        }
    }

    togglePlay() {
        if (this.audioPlayer.paused) {
            if (this.currentSegmentIndex === -1) {
                this.playSegment(0);
            } else {
                this.audioPlayer.play();
            }
        } else {
            this.audioPlayer.pause();
        }
    }

    previousSegment() {
        if (this.currentSegmentIndex > 0) {
            this.playSegment(this.currentSegmentIndex - 1);
        }
    }

    nextSegment() {
        const segments = this.playingMarkedOnly ? this.markedSegments : this.currentTranscript;
        if (this.currentSegmentIndex < segments.length - 1) {
            this.playSegment(this.currentSegmentIndex + 1);
        }
    }

    replaySegment() {
        if (this.currentSegmentIndex !== -1) {
            this.playSegment(this.currentSegmentIndex);
        }
    }

    handleAudioPlay() {
        this.playButton.querySelector('i').textContent = '⏸️';
        this.updateControlState();
        if(this.currentSegmentIndex === -1){
            this.currentSegmentIndex = 0;
        }
    }

    handleAudioPause() {
        this.playButton.querySelector('i').textContent = '▶️';
        this.updateControlState();
    }

    updateControlState() {
        const hasTranscript = this.currentTranscript !== null;
        const hasSegments = hasTranscript && this.currentTranscript.length > 0;
        
        // Update play button
        this.playButton.disabled = !hasSegments;
        
        if (this.playingMarkedOnly) {
            const prevMarked = this.markedSegments.length > 0 && this.currentSegmentIndex > 0;
            const nextMarked = this.markedSegments.length > 0 && this.currentSegmentIndex < this.markedSegments.length - 1;
            this.prevButton.disabled = !prevMarked;
            this.nextButton.disabled = !nextMarked;
        } else {
            this.prevButton.disabled = !hasSegments || this.currentSegmentIndex <= 0;
            this.nextButton.disabled = !hasSegments || this.currentSegmentIndex >= this.currentTranscript.length - 1;
        }
        
        this.replayButton.disabled = !hasSegments || this.currentSegmentIndex === -1;
    }

    markVideoAsPlayed(videoId) {
        this.playedVideos.add(videoId);
        localStorage.setItem('playedVideos', JSON.stringify([...this.playedVideos]));
        
        // Update UI to show played state
        const videoItems = document.querySelectorAll('.video-item');
        videoItems.forEach(item => {
            if (item.dataset.videoId === videoId) {
                item.classList.add('played');
            }
        });
    }

    getPlayedVideos() {
        const played = localStorage.getItem('playedVideos');
        return played ? JSON.parse(played) : [];
    }

    async getSummaryWithOpenAI(transcript) {
        try {
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: `Please provide a concise summary of the following transcript:\n${transcript}`,
                    source_lang: 'auto',
                    target_lang: 'en',
                    service: 'openai'
                })
            });
            const data = await response.json();
            return data.translation;
        } catch (error) {
            console.error('Error getting summary with OpenAI:', error);
            throw error;
        }
    }

    async getSummary(endPoint, model, apiKey, transcript, target_language) {
        try {
            const response = await axios.post(endPoint,
                {
                    model: model,
                    messages: [
                        {
                            role: "system",
                            content: "You are a professional editor."
                        },
                        {
                            role: "user",
                            content: `Give me the summary in language of ${target_language} for this transcript: ${transcript} less than 1000 words. And just give me the summary as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Ali:', error);
            return '';
        }        
    }

    async getSummaryWithAli(apiKey, transcript, target_language) {
        try {
            const response = await axios.post(
                'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
                {
                    model: "qwen-plus",
                    messages: [
                        {
                            role: "system",
                            content: "You are a professional editor."
                        },
                        {
                            role: "user",
                            content: `Give me the summary in language of ${target_language} for this transcript: ${transcript} . And just give me the summary as response.`
                        }
                    ]
                },
                {
                    headers: {
                        'Authorization': 'Bearer ' + apiKey,
                        'Content-Type': 'application/json'
                    }
                }
            );
    
            if (response.data && response.data.choices && response.data.choices.length > 0) {
                return response.data.choices[0].message.content;
            } else {
                console.error('Unexpected response structure:', response.data);
                return '';
            }
        } catch (error) {
            console.error('Error translating with Ali:', error);
            return '';
        }
    }

    async getSummaryWithHunyuan(transcript) {
        try {
            const response = await fetch('/api/translate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: `Please provide a concise summary of the following transcript:\n${transcript}`,
                    source_lang: 'auto',
                    target_lang: 'en',
                    service: 'hunyuan'
                })
            });
            const data = await response.json();
            return data.translation;
        } catch (error) {
            console.error('Error getting summary with Hunyuan:', error);
            throw error;
        }
    }

    async saveSummary(summaryText, service) {
        try {
            await fetch(`/api/summary/${this.currentVideoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    summary_text: summaryText,
                    llm_service: service
                })
            });
        } catch (error) {
            console.error('Error saving summary:', error);
            throw error;
        }
    }

    async getExistingSummaries() {
        try {
            const response = await fetch(`/api/summary/${this.currentVideoId}`);
            return await response.json();
        } catch (error) {
            console.error('Error getting existing summaries:', error);
            return [];
        }
    }

    async handleSummaryRequest() {
        if (!this.currentTranscript || this.currentTranscript.length == 0) {
            this.showToast(window.translations.NoTranscriptForSummary, 'error');
            this.summaryButton.disabled = true;
            this.showSummary("");
            return;
        }

        this.summaryButton.disabled = true;
        this.summaryButton.textContent = window.translations.Fetching;

        try {
            // Check for existing summaries first
            const existingSummaries = await this.getExistingSummaries();
            if (existingSummaries.length > 0) {
                const summary = existingSummaries[0].summary_text;
                this.showSummary(summary);
                // this.showToast('Summary loaded', 'info');
                return;
            }

            // Get full transcript text
            const transcriptText = this.currentTranscript
                .map(segment => segment.text)
                .join(' ');

            const response = await fetch('/api/settings');
            const settings = await response.json();
            const targetLanguage = settings.target_language || 'en';
            if(settings["default_llm"] == "none" || (settings["default_llm"] != "none" && !settings[settings["default_llm"] + "_key"])) {
                this.showToast(window.translations.apiKeyMissing, 'error');
                return;
            }

            let summary = null;
            let endPoint = "";
            let model = "";
            let apiKey = settings[settings["default_llm"] + "_key"];

            if(settings["default_llm"] == "alibaba"){
                endPoint = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions";
                model = "qwen-plus";
                summary = await this.getSummary(endPoint, model, apiKey, transcriptText, targetLanguage);
            }else if(settings["default_llm"] == "openai"){
                endPoint = "https://api.openai.com/v1/chat/completions";
                model = "gpt-3.5-turbo";
                summary = await this.getSummary(endPoint, model, apiKey, transcriptText, targetLanguage);
            }else if(settings["default_llm"] == "hunyuan"){
                endPoint = "https://api.hunyuan.cloud.tencent.com/v1/chat/completions";
                model = "hunyuan-turbo";
                summary = await this.getSummary(endPoint, model, apiKey, transcriptText, targetLanguage);
            }else{
                this.showToast(window.translations.summarizeFailed, 'error');
                return;
            }
                        
            if (summary) {
                await this.saveSummary(summary, 'alibaba');
                this.showSummary(summary);
                // this.showToast('Summary generated successfully', 'success');
            } else {
                this.showToast(window.translations.summarizeFailed, 'error');
            }

        } catch (error) {
            console.error('Error handling summary request:', error);
            this.showToast(window.translations.summarizeFailed, 'error');
        } finally {
            this.summaryButton.disabled = false;
            this.summaryButton.textContent = window.translations.Summary;
        }
    }

    showSummary(summary) {
        this.summaryContent.textContent = summary;
        this.summaryContainer.style.display = 'block';
        
        // Adjust transcript container width when summary is shown
        const transcriptContainer = document.getElementById('transcript-container');
        transcriptContainer.style.flex = '1';
    }
}

// Add keyboard event listener for space key to toggle audio playback
document.addEventListener('keydown', function(event) {
    console.log("Key pressed:", event.code);
    if (event.code === 'Space') {
        const audio = document.querySelector('audio');
        if (audio) {
            if (audio.paused) {
                audio.play();
            } else {
                audio.pause();
            }
        }
        event.preventDefault();
        event.stopPropagation();
    }else if (event.key === 'ArrowLeft'){
        window.player.previousSegment();            
        event.preventDefault();
        event.stopPropagation();
    }else if (event.key === 'ArrowRight'){
        window.player.nextSegment();            
        event.preventDefault();
        event.stopPropagation();
    }
});

// Initialize player when the page is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing AudioTubePlayer');
    window.player = new AudioTubePlayer();
});
