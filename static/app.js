/**
 * CineMatch AI - Modern Frontend Client Engine
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Element References
  const searchInput = document.getElementById('search-input');
  const clearBtn = document.getElementById('clear-btn');
  const searchBtn = document.getElementById('search-btn');
  
  // Custom Dark Dropdown
  const dropdownTrigger = document.getElementById('dropdown-trigger');
  const dropdownMenu = document.getElementById('dropdown-menu');
  const selectedTopNText = document.getElementById('selected-top-n');
  const autocompleteList = document.getElementById('autocomplete-list');

  const errorContainer = document.getElementById('error-container');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const errorSuggestions = document.getElementById('error-suggestions');

  const loadingState = document.getElementById('loading-state');
  const resultsSection = document.getElementById('results-section');
  const targetMovieContainer = document.getElementById('target-movie-container');
  const recommendationsGrid = document.getElementById('recommendations-grid');

  const catalogGrid = document.getElementById('catalog-grid');
  const genreFilter = document.getElementById('genre-filter');
  const sortSelect = document.getElementById('sort-select');
  const prevPageBtn = document.getElementById('prev-page');
  const nextPageBtn = document.getElementById('next-page');
  const pageIndicator = document.getElementById('page-indicator');

  const movieModal = document.getElementById('movie-modal');
  const modalClose = document.getElementById('modal-close');
  const modalBody = document.getElementById('modal-body');

  // Application State
  let selectedTopNValue = 5;
  let currentPage = 1;
  let totalCatalogPages = 1;
  let debounceTimer = null;
  let activeMoviesMap = new Map();

  // Initialization
  initStatsAndGenres();
  loadCatalog(1);
  setupEventListeners();

  // Load App Stats and Genre Filters
  async function initStatsAndGenres() {
    try {
      const res = await fetch('/api/stats');
      if (!res.ok) return;
      const data = await res.json();
      
      if (data.genres && Array.isArray(data.genres)) {
        data.genres.forEach(genre => {
          const opt = document.createElement('option');
          opt.value = genre;
          opt.textContent = genre;
          genreFilter.appendChild(opt);
        });
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  }

  // Setup Event Listeners
  function setupEventListeners() {
    // Custom Dark Dropdown Toggle
    dropdownTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdownMenu.classList.toggle('hidden');
    });

    document.querySelectorAll('#dropdown-menu .dropdown-item').forEach(item => {
      item.addEventListener('click', (e) => {
        e.stopPropagation();
        document.querySelectorAll('#dropdown-menu .dropdown-item').forEach(i => i.classList.remove('active'));
        item.classList.add('active');
        selectedTopNValue = parseInt(item.getAttribute('data-value'), 10) || 5;
        selectedTopNText.textContent = `Top ${selectedTopNValue}`;
        dropdownMenu.classList.add('hidden');
      });
    });

    // Close dropdowns on outside click
    document.addEventListener('click', () => {
      dropdownMenu.classList.add('hidden');
      autocompleteList.classList.add('hidden');
    });

    // Search input typing & autocomplete debounce
    searchInput.addEventListener('input', (e) => {
      const val = e.target.value.trim();
      clearBtn.classList.toggle('hidden', val.length === 0);

      clearTimeout(debounceTimer);
      if (val.length < 2) {
        autocompleteList.classList.add('hidden');
        return;
      }

      debounceTimer = setTimeout(() => fetchAutocomplete(val), 250);
    });

    // Clear search button
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      clearBtn.classList.add('hidden');
      autocompleteList.classList.add('hidden');
      searchInput.focus();
    });

    // Search button click
    searchBtn.addEventListener('click', () => {
      const title = searchInput.value.trim();
      if (title) fetchRecommendations(title);
    });

    // Enter key press in search box
    searchInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        const title = searchInput.value.trim();
        if (title) fetchRecommendations(title);
      }
    });

    // Quick Pick Tags
    document.querySelectorAll('.tag-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const title = btn.getAttribute('data-movie');
        if (title) {
          searchInput.value = title;
          clearBtn.classList.remove('hidden');
          fetchRecommendations(title);
        }
      });
    });

    // Catalog Controls
    genreFilter.addEventListener('change', () => loadCatalog(1));
    sortSelect.addEventListener('change', () => loadCatalog(1));
    
    prevPageBtn.addEventListener('click', () => {
      if (currentPage > 1) loadCatalog(currentPage - 1);
    });

    nextPageBtn.addEventListener('click', () => {
      if (currentPage < totalCatalogPages) loadCatalog(currentPage + 1);
    });

    // Close Modal
    modalClose.addEventListener('click', closeModal);
    movieModal.addEventListener('click', (e) => {
      if (e.target === movieModal) closeModal();
    });
  }

  // Fetch Search Autocomplete with Poster Thumbnails
  async function fetchAutocomplete(query) {
    try {
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=6`);
      if (!res.ok) return;
      const data = await res.json();
      
      autocompleteList.innerHTML = '';
      if (!data.results || data.results.length === 0) {
        autocompleteList.classList.add('hidden');
        return;
      }

      data.results.forEach(movie => {
        const item = document.createElement('div');
        item.className = 'autocomplete-item';
        const year = movie.release_date ? movie.release_date.slice(0, 4) : '';
        const genreText = movie.genres ? movie.genres.slice(0, 2).join(', ') : '';

        item.innerHTML = `
          <img src="${movie.poster_url}" alt="${escapeHtml(movie.title)}" class="autocomplete-poster-thumb">
          <div class="autocomplete-info">
            <div class="autocomplete-title">${escapeHtml(movie.title)}</div>
            <div class="autocomplete-meta">${year} ${genreText ? '• ' + escapeHtml(genreText) : ''}</div>
          </div>
          <span class="rating-badge">★ ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}</span>
        `;

        item.addEventListener('click', () => {
          searchInput.value = movie.title;
          autocompleteList.classList.add('hidden');
          fetchRecommendations(movie.title);
        });

        autocompleteList.appendChild(item);
      });

      autocompleteList.classList.remove('hidden');
    } catch (err) {
      console.error('Autocomplete error:', err);
    }
  }

  // Fetch Recommendations for Title
  async function fetchRecommendations(title) {
    autocompleteList.classList.add('hidden');
    errorContainer.classList.add('hidden');
    resultsSection.classList.add('hidden');
    loadingState.classList.remove('hidden');

    try {
      const res = await fetch(`/api/recommend?title=${encodeURIComponent(title)}&top=${selectedTopNValue}`);
      const data = await res.json();

      loadingState.classList.add('hidden');

      if (!res.ok || data.error) {
        showError(data.error || 'Movie not found in database.', data.suggestions || []);
        return;
      }

      displayResults(data.target_movie, data.recommendations);
    } catch (err) {
      loadingState.classList.add('hidden');
      showError('Failed to connect to recommendation server.', []);
      console.error(err);
    }
  }

  // Show Error Card
  function showError(msg, suggestions) {
    errorTitle.textContent = 'Movie Search Result';
    errorMessage.textContent = msg;
    errorSuggestions.innerHTML = '';

    if (suggestions && suggestions.length > 0) {
      suggestions.forEach(m => {
        const btn = document.createElement('button');
        btn.className = 'tag-btn';
        btn.textContent = m.title;
        btn.addEventListener('click', () => {
          searchInput.value = m.title;
          fetchRecommendations(m.title);
        });
        errorSuggestions.appendChild(btn);
      });
    }

    errorContainer.classList.remove('hidden');
    errorContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  // Display Target Movie & Recommendations Banner & Grid
  function displayResults(targetMovie, recommendations) {
    activeMoviesMap.set(targetMovie.movie_id, targetMovie);
    recommendations.forEach(r => activeMoviesMap.set(r.movie_id, r));

    // 1. Render Target Movie Banner
    const targetGenres = (targetMovie.genres || []).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join(' ');
    const directorName = (targetMovie.director || []).join(', ') || 'N/A';
    const castNames = (targetMovie.cast || []).join(', ') || 'N/A';
    const releaseYear = targetMovie.release_date ? targetMovie.release_date.slice(0, 4) : 'N/A';

    targetMovieContainer.innerHTML = `
      <img src="${targetMovie.poster_url}" alt="${escapeHtml(targetMovie.title)}" class="target-poster">
      <div class="target-info">
        <h3>${escapeHtml(targetMovie.title)}</h3>
        <div class="target-meta">
          <span class="rating-badge">★ ${targetMovie.vote_average ? targetMovie.vote_average.toFixed(1) : 'N/A'} / 10</span>
          <span>📅 ${releaseYear}</span>
          ${targetMovie.runtime ? `<span>⏱️ ${targetMovie.runtime} mins</span>` : ''}
          ${targetGenres}
        </div>
        <p class="target-overview">${escapeHtml(targetMovie.overview || 'No overview available.')}</p>
        <div class="target-crew">
          <span><strong>Director:</strong> ${escapeHtml(directorName)}</span>
          <span><strong>Cast:</strong> ${escapeHtml(castNames)}</span>
        </div>
      </div>
    `;

    // 2. Render Recommended Movies Grid
    recommendationsGrid.innerHTML = '';
    recommendations.forEach(movie => {
      const card = createMovieCard(movie, true);
      recommendationsGrid.appendChild(card);
    });

    resultsSection.classList.remove('hidden');
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Load Catalog Page
  async function loadCatalog(page = 1) {
    const genre = genreFilter.value;
    const sortBy = sortSelect.value;
    const limit = 12;

    try {
      const res = await fetch(`/api/movies?page=${page}&limit=${limit}&genre=${encodeURIComponent(genre)}&sort_by=${sortBy}`);
      if (!res.ok) return;
      const data = await res.json();

      currentPage = data.page;
      totalCatalogPages = Math.ceil(data.total / limit);

      catalogGrid.innerHTML = '';
      data.movies.forEach(movie => {
        activeMoviesMap.set(movie.movie_id, movie);
        const card = createMovieCard(movie, false);
        catalogGrid.appendChild(card);
      });

      // Update Pagination controls
      pageIndicator.textContent = `Page ${currentPage} of ${totalCatalogPages || 1}`;
      prevPageBtn.disabled = currentPage <= 1;
      nextPageBtn.disabled = currentPage >= totalCatalogPages;

    } catch (err) {
      console.error('Catalog load error:', err);
    }
  }

  // Create Single Movie Card Element
  function createMovieCard(movie, showMatch = false) {
    const card = document.createElement('div');
    card.className = 'movie-card';

    const genresHtml = (movie.genres || []).slice(0, 2).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join(' ');
    const year = movie.release_date ? movie.release_date.slice(0, 4) : '';

    card.innerHTML = `
      <div class="card-poster-wrapper">
        <img src="${movie.poster_url}" alt="${escapeHtml(movie.title)}" class="card-poster" loading="lazy">
        ${showMatch ? `<div class="match-badge">${movie.match_percentage}% Match</div>` : ''}
      </div>
      <div class="card-content">
        <h4 class="card-title">${escapeHtml(movie.title)}</h4>
        <div class="card-meta">
          <span>📅 ${year}</span>
          <span class="rating-badge">★ ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'}</span>
        </div>
        <div class="card-genres">${genresHtml}</div>
        <div class="card-actions">
          <button class="btn btn-secondary btn-detail">Details</button>
          <button class="btn btn-primary btn-rec">Similar</button>
        </div>
      </div>
    `;

    // Button event listeners
    card.querySelector('.btn-detail').addEventListener('click', (e) => {
      e.stopPropagation();
      openModal(movie);
    });

    card.querySelector('.btn-rec').addEventListener('click', (e) => {
      e.stopPropagation();
      searchInput.value = movie.title;
      fetchRecommendations(movie.title);
    });

    card.addEventListener('click', () => openModal(movie));

    return card;
  }

  // Open Movie Details Modal
  function openModal(movie) {
    const genres = (movie.genres || []).map(g => `<span class="genre-pill">${escapeHtml(g)}</span>`).join(' ');
    const keywords = (movie.keywords || []).map(k => `<span class="tag-btn">${escapeHtml(k)}</span>`).join(' ');
    const director = (movie.director || []).join(', ') || 'N/A';
    const cast = (movie.cast || []).join(', ') || 'N/A';
    const releaseYear = movie.release_date || 'N/A';

    const youtubeSearchUrl = `https://www.youtube.com/results?search_query=${encodeURIComponent(movie.title + ' official trailer')}`;

    modalBody.innerHTML = `
      <div class="modal-grid">
        <div>
          <img src="${movie.poster_url}" alt="${escapeHtml(movie.title)}" class="modal-poster">
        </div>
        <div>
          <h2 style="font-size: 1.8rem; margin-bottom: 0.5rem;">${escapeHtml(movie.title)}</h2>
          <div class="target-meta" style="margin-bottom: 1rem;">
            <span class="rating-badge">★ ${movie.vote_average ? movie.vote_average.toFixed(1) : 'N/A'} / 10 (${movie.vote_count || 0} votes)</span>
            <span>📅 ${releaseYear}</span>
            ${movie.runtime ? `<span>⏱️ ${movie.runtime} mins</span>` : ''}
          </div>
          <div style="margin-bottom: 1rem;">${genres}</div>
          <p style="color: var(--text-muted); margin-bottom: 1.25rem; font-size: 0.95rem;">${escapeHtml(movie.overview || 'No overview available.')}</p>
          <div style="font-size: 0.9rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1.5rem;">
            <div><strong>Director:</strong> ${escapeHtml(director)}</div>
            <div><strong>Starring Cast:</strong> ${escapeHtml(cast)}</div>
          </div>
          <div style="margin-bottom: 1.5rem;">
            <h4 style="font-size: 0.9rem; color: var(--text-subtle); margin-bottom: 0.5rem;">KEYWORDS</h4>
            <div style="display: flex; gap: 0.35rem; flex-wrap: wrap;">${keywords || 'None'}</div>
          </div>
          <div style="display: flex; gap: 0.75rem;">
            <button id="modal-recommend-btn" class="btn btn-primary">Find Similar Movies</button>
            <a href="${youtubeSearchUrl}" target="_blank" rel="noopener" class="btn btn-secondary" style="text-decoration: none;">▶ Watch Trailer</a>
          </div>
        </div>
      </div>
    `;

    document.getElementById('modal-recommend-btn').addEventListener('click', () => {
      closeModal();
      searchInput.value = movie.title;
      fetchRecommendations(movie.title);
    });

    movieModal.classList.remove('hidden');
  }

  function closeModal() {
    movieModal.classList.add('hidden');
  }

  function escapeHtml(str) {
    if (typeof str !== 'string') return '';
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
});
