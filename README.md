# TMDB Movie Recommendation System

A Content-Based Movie Recommendation System built using Python, Pandas, Scikit-Learn, and NLTK. This system recommends movies similar to a user's favorite movie by analyzing movie attributes such as genres, keywords, cast, crew, and plot summaries.

---

## 🚀 How it Works

The recommendation engine utilizes **Content-Based Filtering** to find similarity between movies. Here is the step-by-step pipeline implemented in this project:

1. **Data Merging**: Combines TMDB 5000 Movies and Credits datasets on the movie title.
2. **Feature Selection**: Selects critical features for recommendation:
   - `movie_id`
   - `title`
   - `overview` (plot summary)
   - `genres`
   - `keywords`
   - `cast` (top 3 actors)
   - `crew` (director)
3. **Data Preprocessing & Cleaning**:
   - Parses stringified JSON fields into Python lists.
   - Cleans names and tags (e.g., removing spaces: `"Science Fiction"` becomes `"ScienceFiction"`, `"Sam Worthington"` becomes `"SamWorthington"`) to prevent tag mismatching.
   - Combines all features into a single consolidated string of `tags` for each movie.
4. **Text Stemming**: Uses NLTK's `PorterStemmer` to reduce words to their root forms (e.g., `"loving"`, `"loved"` -> `"love"`).
5. **Vectorization**: Transforms the text tags into numerical vectors using Scikit-Learn's `CountVectorizer` (using a Bag of Words model with the top 5000 features, ignoring common English stop words).
6. **Cosine Similarity**: Calculates the cosine distance between movie vectors to construct a similarity matrix.
7. **Recommendation**: Finds the top 5 most similar movies based on the similarity scores.

---

## 📂 Project Structure

```
├── tmdb_5000_movies.csv       # TMDB dataset containing movie metadata
├── tmdb_5000_credits.csv      # TMDB dataset containing cast and crew info
├── main.ipynb                 # Jupyter Notebook containing data pipeline & model
├── README.md                  # Project documentation
├── .gitignore                 # Files to ignore in Git
```

---

## 🛠️ Installation & Setup

To run this project locally, you need Python and the required data science libraries.

### 1. Clone the Repository
```bash
git clone https://github.com/Minhaj078/Movie_Recommendation_System.git
cd Movie_Recommendation_System
```

### 2. Install Dependencies
Make sure you have `pip` installed, then run:
```bash
pip install numpy pandas scikit-learn nltk
```

### 3. Run the Jupyter Notebook
Start Jupyter Notebook or open the project in VS Code:
```bash
jupyter notebook main.ipynb
```
Run all cells in `main.ipynb` to preprocess the dataset, train the recommender model, and generate the similarity matrices.

---

## 🔮 Usage

Once the notebook runs successfully, you can get recommendations using the `recommend` function:

```python
recommend('Avatar')
```

**Output Example:**
```text
Aliens
Silent Running
Mission to Mars
Moon
Alien vs. Predator
```

---

## 🎯 Future Enhancements
- 🖥️ **Web Application**: Build an interactive web frontend using **Streamlit** or **Flask** to allow users to select movies from a dropdown.
- 🎬 **Movie Posters**: Integrate the TMDB API to fetch and display high-quality posters for the recommended movies.
- 🤝 **Collaborative Filtering**: Implement collaborative or hybrid filtering to improve suggestion accuracy using user rating data.
