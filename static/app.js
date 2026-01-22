const searchBtn = document.getElementById('searchBtn');
const queryInput = document.getElementById('queryInput');
const resultsGrid = document.getElementById('resultsGrid');
const loading = document.getElementById('loading');
const resultsInfo = document.getElementById('resultsInfo');
const matchCount = document.getElementById('matchCount');

// Filters
const levelMin = document.getElementById('levelMin');
const levelMax = document.getElementById('levelMax');
const bpmMin = document.getElementById('bpmMin');
const bpmMax = document.getElementById('bpmMax');
const designerInput = document.getElementById('designerInput');
const diffToggles = document.getElementsByClassName('diff-btn');

// Toggle Logic
Array.from(diffToggles).forEach(btn => {
    btn.addEventListener('click', () => {
        btn.classList.toggle('active');
    });
});

async function performSearch() {
    const query = queryInput.value.trim();
    if (!query) return;

    // Show loading
    loading.style.display = 'block';
    resultsGrid.innerHTML = '';
    resultsInfo.style.display = 'none';

    // Collect filters
    const params = new URLSearchParams();
    params.append('query', query);

    if (levelMin.value) params.append('level_min', levelMin.value);
    if (levelMax.value) params.append('level_max', levelMax.value);
    if (bpmMin.value) params.append('bpm_min', bpmMin.value);
    if (bpmMax.value) params.append('bpm_max', bpmMax.value);
    if (designerInput.value) params.append('designer', designerInput.value);

    const activeDiffs = Array.from(diffToggles)
        .filter(btn => btn.classList.contains('active'))
        .map(btn => btn.dataset.val);

    if (activeDiffs.length > 0) {
        params.append('diff', activeDiffs.join(','));
    }

    try {
        const response = await fetch(`/api/search?${params.toString()}`);
        const data = await response.json();

        if (data.error) {
            alert(data.error);
            return;
        }

        renderResults(data.results);
        matchCount.innerText = data.count;
        resultsInfo.style.display = 'block';

    } catch (err) {
        console.error(err);
        alert("Search failed. Check console.");
    } finally {
        loading.style.display = 'none';
    }
}

function renderResults(results) {
    resultsGrid.innerHTML = results.map(res => {
        const percent = Math.round((res.match_degree || 0) * 100);
        return `
        <div class="result-card">
            <div class="card-header">
                <div>
                    <div class="song-title">${res.title}</div>
                    <div style="color: var(--text-muted); font-size: 0.85rem;">Level ${res.level}</div>
                </div>
                <div style="text-align: right;">
                    <div class="diff-badge diff-${res.difficulty}">${res.difficulty}</div>
                    <div style="margin-top:4px; font-size: 0.8rem; color: var(--primary);">Match: ${percent}%</div>
                </div>
            </div>
            <div class="snippet-box">${res.snippet}</div>
        </div>
    `}).join('');
}

searchBtn.addEventListener('click', performSearch);
queryInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') performSearch();
});
