# 🎬 CineMatch AI - TMDB Movie Recommendation System

A modern, production-ready **Full-Stack Content-Based Movie Recommendation System** built with **Python, Scikit-Learn, NLTK, Flask**, and a sleek **Dark Glassmorphic Web UI**.

This application recommends movies similar to your favorite films by analyzing plot overviews, genres, keywords, cast, and directors using **Natural Language Processing (NLP)** and **Cosine Similarity**.

---

## ✨ Features

- 🧠 **Machine Learning Engine**: Content-based filtering using `CountVectorizer` and NLTK `PorterStemmer` text vectorization with cosine similarity scoring.
- 🎨 **Modern Dark Glassmorphic UI**: High-end cinema design with gradient highlights (`#6366f1` & `#ec4899`), glassmorphic cards, ambient glow orbs, and dark backdrop blur.
- 🔍 **Real-Time Autocomplete Search**: Instant title autocompletion featuring movie poster thumbnails, release year, genres, and rating badges.
- 🎛️ **Custom Dark Dropdown**: Custom recommendation count selector (`Top 5`, `Top 8`, `Top 12`, `Top 16`).
- 🖼️ **Dynamic Movie Poster Art**: High-resolution movie posters across autocomplete items, target movie banners, recommendation grids, and catalog cards.
- 🍿 **Interactive Movie Modal**: Detailed movie popup showcasing full synopsis, director, cast list, keywords, and a direct YouTube trailer button.
- 📚 **Explore Movie Catalog**: Filterable catalog grid supporting genre filtering (`Action`, `Sci-Fi`, `Drama`, etc.), sorting (`Popularity`, `Rating`, `Title`), and pagination.
- 🛡️ **Robust Error Handling**: Graceful fallback handling for non-existent titles, empty searches, special characters, and missing inputs.

---

## 🛠️ Tech Stack

- **Backend & API**: Python 3, Flask, Flask-CORS, Gunicorn
- **Data Science & ML**: Pandas, NumPy, Scikit-Learn (`CountVectorizer`, `cosine_similarity`), NLTK (`PorterStemmer`)
- **Frontend**: HTML5, Vanilla JavaScript (ES6+), Modern CSS3 Custom Properties & Glassmorphism
- **Deployment Ready**: Configured for Render, Vercel, Railway, and Heroku

---

## 📁 Project Structure

```
Movie_Recommendation_System/
├── artifacts/                  # Generated binary model files
│   ├── movies_dict.pkl         # Clean movie metadata list
│   └── similarity.pkl          # Cosine similarity matrix (4806 x 4806)
├── static/                     # Frontend static assets
│   ├── index.html              # Modern single-page web app UI
│   ├── styles.css              # Dark glassmorphic design system
│   └── app.js                  # Client logic, autocomplete, and REST calls
├── app.py                      # Flask REST API server & static server
├── builder.py                  # Preprocessing, bug fixes, & artifact generator
├── tmdb_5000_movies.csv        # TMDB 5000 movies dataset
├── tmdb_5000_credits.csv       # TMDB 5000 credits (cast & crew) dataset
├── requirements.txt            # Python dependencies
├── Procfile                    # Web server deployment file
├── vercel.json                 # Vercel serverless configuration
└── README.md                   # Project documentation
```

---

## 🚀 How to Run the Application Locally

### Step 1: Open Terminal in Project Directory
Ensure your terminal or command prompt is located inside the `Movie_Recommendation_System` directory:
```bash
cd Movie_Recommendation_System
```

### Step 2: Install Required Dependencies
Run the following command to install Flask, Scikit-Learn, Pandas, and required packages:
```bash
py -3 -m pip install -r requirements.txt
```
*(Or use `pip install -r requirements.txt` depending on your environment)*

### Step 3: Build & Export Data Artifacts (One-Time Setup)
Generate the pre-computed recommendations matrix and clean metadata pickle files:
```bash
py -3 builder.py
```
*Output expectation:*
```text
[+] Loading TMDB 5000 datasets...
[+] Merging datasets on title...
[+] Cleaning & extracting features...
[+] Stemming text tags with NLTK PorterStemmer...
[+] Vectorizing tags with CountVectorizer...
[+] Calculating Cosine Similarity Matrix...
[+] Saving model artifacts...
✅ Model build & export complete successfully!
Total Movies: 4806
```

### Step 4: Start the Web Server
Launch the Flask API server:
```bash
py -3 app.py
```
*Output expectation:*
```text
[+] Loading artifacts into memory...
[+] Loaded 4806 movies into memory!
🚀 Starting Movie Recommendation API Server on http://127.0.0.1:5000
```

### Step 5: Open in Your Browser
Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🧪 How to Run QA & Unit Tests

To verify that all API endpoints, logic fixes, security sanitization, and edge cases are passing:

Run the comprehensive QA test suite:
```bash
py -3 -m unittest discover -s . -p "test_*.py"
```

Or run the specific edge case test script:
```bash
py -3 scratch/test_edge_cases.py
```
*Output expectation:*
```text
..........
Ran 10 tests in 0.043s
OK
```

---

## 📡 API Endpoints Reference

| Endpoint | Method | Description | Sample Query |
| :--- | :--- | :--- | :--- |
| `GET /api/recommend` | `GET` | Get recommendations for a movie title | `/api/recommend?title=Avatar&top=5` |
| `GET /api/search` | `GET` | Autocomplete title search with posters | `/api/search?q=iron&limit=6` |
| `GET /api/movies` | `GET` | Paginated catalog with genre filtering | `/api/movies?page=1&limit=12&genre=Action` |
| `GET /api/stats` | `GET` | Dataset metrics & available genres | `/api/stats` |

---

## 🌐 Production Deployment

### Option 1: Deploy on Render / Railway
1. Push your repository to GitHub.
2. Create a **Web Service** on Render or Railway.
3. Set the build command: `pip install -r requirements.txt && python builder.py`
4. Set the start command: `gunicorn app:app`

### Option 2: Deploy on Vercel
1. Install Vercel CLI: `npm i -g vercel`
2. Run `vercel` in the project root directory.

---

## 📜 License & Credits

- Dataset sourced from **TMDB (The Movie Database)** 5000 Dataset.
- Built with Python, Flask, Scikit-Learn, and NLTK.
