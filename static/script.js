const submitBtn = document.getElementById('submitBtn');
const repoUrlInput = document.getElementById('repoUrl');
const queryInput = document.getElementById('query');
const resultsSection = document.getElementById('results');
const answerContent = document.getElementById('answerContent');
const sourcesContainer = document.getElementById('sourcesContainer');
const sourcesList = document.getElementById('sourcesList');
const errorDiv = document.getElementById('error');
const btnText = document.querySelector('.btn-text');
const btnLoading = document.querySelector('.btn-loading');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingTitle = document.getElementById('loadingTitle');
const loadingMessage = document.getElementById('loadingMessage');
const progressFill = document.getElementById('progressFill');
const loadingSteps = document.getElementById('loadingSteps');

const processingSteps = [
    { id: 'clone', label: 'Cloning repository', progress: 20 },
    { id: 'parse', label: 'Parsing code files', progress: 40 },
    { id: 'chunk', label: 'Chunking documents', progress: 60 },
    { id: 'embed', label: 'Creating embeddings', progress: 80 },
    { id: 'query', label: 'Querying AI model', progress: 90 },
    { id: 'complete', label: 'Processing complete', progress: 100 }
];

const cachedSteps = [
    { id: 'load', label: 'Loading cached database', progress: 30 },
    { id: 'query', label: 'Querying AI model', progress: 70 },
    { id: 'complete', label: 'Processing complete', progress: 100 }
];

submitBtn.addEventListener('click', handleSubmit);

queryInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        handleSubmit();
    }
});

async function handleSubmit() {
    const repoUrl = repoUrlInput.value.trim();
    const query = queryInput.value.trim();

    if (!repoUrl || !query) {
        showError('Please enter both repository URL and your question.');
        return;
    }

    if (!isValidGitHubUrl(repoUrl)) {
        showError('Please enter a valid GitHub repository URL.');
        return;
    }

    hideError();

    // Check if repo is cached
    const isCached = await checkIfCached(repoUrl);
    showLoadingScreen(isCached);

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                repo_url: repoUrl,
                query: query
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Failed to process request');
        }

        const data = await response.json();
        hideLoadingScreen();
        displayResults(data, isCached);
    } catch (error) {
        hideLoadingScreen();
        showError(`Error: ${error.message}`);
    }
}

async function checkIfCached(repoUrl) {
    try {
        const response = await fetch('/api/db-status');
        const data = await response.json();

        // Simple check - if any DB exists, assume it might be cached
        // In production, you'd want to match the repo URL more precisely
        return data.total > 0;
    } catch (error) {
        return false;
    }
}

function showLoadingScreen(isCached = false) {
    loadingOverlay.style.display = 'flex';
    loadingSteps.innerHTML = '';

    const steps = isCached ? cachedSteps : processingSteps;
    const title = isCached ? 'Using Cached Repository ⚡' : 'Processing Repository';
    loadingTitle.textContent = title;

    steps.forEach((step, index) => {
        const stepEl = document.createElement('div');
        stepEl.className = 'loading-step';
        stepEl.id = `step-${step.id}`;
        stepEl.innerHTML = `
            <div class="step-icon">
                ${index === 0 ? '<div class="step-spinner"></div>' : getStepIcon('pending')}
            </div>
            <span>${step.label}</span>
        `;
        loadingSteps.appendChild(stepEl);
    });

    simulateProgress(steps);
}

function hideLoadingScreen() {
    loadingOverlay.style.display = 'none';
    progressFill.style.width = '0%';
}

function simulateProgress(steps = processingSteps) {
    let currentStep = 0;
    const interval = steps.length === 3 ? 800 : 1500; // Faster for cached

    const progressInterval = setInterval(() => {
        if (currentStep < steps.length) {
            const step = steps[currentStep];

            updateStepStatus(currentStep, 'active', steps);
            loadingMessage.textContent = step.label;
            progressFill.style.width = step.progress + '%';

            if (currentStep > 0) {
                updateStepStatus(currentStep - 1, 'completed', steps);
            }

            currentStep++;
        } else {
            clearInterval(progressInterval);
        }
    }, interval);
}

function updateStepStatus(stepIndex, status, steps = processingSteps) {
    const step = steps[stepIndex];
    const stepEl = document.getElementById(`step-${step.id}`);

    if (stepEl) {
        stepEl.className = `loading-step ${status}`;
        const iconEl = stepEl.querySelector('.step-icon');

        if (status === 'active') {
            iconEl.innerHTML = '<div class="step-spinner"></div>';
        } else if (status === 'completed') {
            iconEl.innerHTML = getStepIcon('completed');
        } else {
            iconEl.innerHTML = getStepIcon('pending');
        }
    }
}

function getStepIcon(type) {
    if (type === 'completed') {
        return `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
    }
    return `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" opacity="0.3">
            <circle cx="12" cy="12" r="10"></circle>
        </svg>
    `;
}

function displayResults(data, isCached = false) {
    // Add cache indicator if cached
    const cacheIndicator = isCached ?
        '<div style="display: inline-block; background: #10b981; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; margin-bottom: 12px;">⚡ Loaded from cache</div>' : '';

    answerContent.innerHTML = cacheIndicator + formatAnswer(data.answer);

    if (data.sources && data.sources.length > 0) {
        sourcesList.innerHTML = data.sources.map(source => `
            <div class="source-item">
                <div class="source-header">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
                        <polyline points="13 2 13 9 20 9"></polyline>
                    </svg>
                    <span class="source-path">${formatSourcePath(source.source)}</span>
                </div>
                <div class="source-content">${escapeHtml(source.content)}</div>
            </div>
        `).join('');
        sourcesContainer.style.display = 'block';
    } else {
        sourcesContainer.style.display = 'none';
    }

    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function formatAnswer(answer) {
    answer = escapeHtml(answer);
    answer = answer.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    answer = answer.replace(/\*(.*?)\*/g, '<em>$1</em>');
    answer = answer.replace(/`(.*?)`/g, '<code>$1</code>');
    answer = answer.replace(/\n\n/g, '</p><p>');
    answer = answer.replace(/\n/g, '<br>');
    return `<p>${answer}</p>`;
}

function formatSourcePath(path) {
    const parts = path.split(/[\\/]/);
    return parts.slice(-3).join('/');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function isValidGitHubUrl(url) {
    const githubPattern = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+\/?$/;
    return githubPattern.test(url);
}

function showError(message) {
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    errorDiv.style.display = 'none';
}