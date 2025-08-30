# Word Jokes - Hungarian Word Play Generator

A Python-based project for discovering and analyzing Hungarian words that can be split into meaningful sub-words, creating linguistic puzzles and word games.

## 🎯 Project Overview

This project analyzes Hungarian vocabulary to find words that can be decomposed into smaller, meaningful sub-words. It's designed to discover linguistic patterns where longer words can be broken down into combinations of shorter words, creating opportunities for word play and language learning.

## 📁 Project Structure

```
word_jokes/
├── README.md                           # This file
├── word_jokes.py                       # Main script for generating word combinations
├── word_jokes.ipynb                    # Jupyter notebook with analysis and examples
├── analyse_words.ipynb                 # XML word analysis notebook
├── joke_analyzer.ipynb                 # Analysis of generated combinations
├── findings                            # Sample findings and word play examples
├── szoviccek                           # Word play rules and guidelines
├── words_hu.csv                        # Hungarian word corpus (1.9MB)
├── stopwords-hu.txt                    # Hungarian stopwords
├── huwn.xml                           # Hungarian WordNet XML data (19MB)
├── all_word_comibations.csv            # All generated word combinations
├── all_filtered_word_comibations.csv   # Filtered valid combinations
├── 3_element_word_comibations.csv     # 3-part word combinations
├── 4_element_word_comibations.csv     # 4-part word combinations
└── 5_element_word_comibations.csv     # 5-part word combinations
```

## 🚀 Features

- **Word Decomposition**: Finds Hungarian words that can be split into meaningful sub-words
- **Multi-part Analysis**: Supports 3, 4, and 5-part word combinations
- **Corpus Processing**: Handles large Hungarian word datasets with filtering
- **Prefix Removal**: Automatically filters out common Hungarian prefixes
- **Stopword Filtering**: Removes common words to focus on meaningful combinations
- **Length Constraints**: Configurable word length limits for combinations

## 📊 Data Sources

- **words_hu.csv**: Main Hungarian word corpus
- **huwn.xml**: Hungarian WordNet data for semantic analysis
- **stopwords-hu.txt**: Hungarian stopwords for filtering

## 🛠️ Requirements

The project requires the following Python packages:
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical operations
- `seaborn` - Data visualization (optional)

## 📖 Usage

### Basic Usage

1. **Generate Word Combinations**:
   ```bash
   python word_jokes.py
   ```

2. **Interactive Analysis**:
   - Open `word_jokes.ipynb` for interactive exploration
   - Use `analyse_words.ipynb` for XML data analysis
   - Check `joke_analyzer.ipynb` for combination analysis

### Configuration

The main script (`word_jokes.py`) includes several configurable parameters:
- `max_size`: Maximum total length for word combinations (default: 14)
- `min_part_len`: Minimum length for individual word parts (default: 2)
- Batch size for processing combinations (default: 50,000,000)

## 🎲 Word Play Examples

The project discovers words like:
- `kandalló` → `kan` + `dal` + `ló`
- `vasárnap` → `vas` + `ár` + `nap`
- `telefon` → `te` + `le` + `fon`

## 🔍 Analysis Features

- **Corpus Statistics**: Word length distribution analysis
- **Combination Generation**: Systematic generation of word combinations
- **Validation**: Filters combinations to ensure meaningful results
- **Performance Monitoring**: Time tracking for long-running operations

## 📈 Output Files

The system generates several CSV files:
- **all_word_comibations.csv**: Complete dataset of all combinations
- **filtered combinations**: Valid combinations meeting criteria
- **Element-specific files**: Separate files for 3, 4, and 5-part combinations

## 🤝 Contributing

To contribute to this project:
1. Analyze the existing notebooks to understand the workflow
2. Modify parameters in `word_jokes.py` for different analysis approaches
3. Add new filtering criteria or analysis methods
4. Share interesting findings in the `findings` file

## 📝 Notes

- The project is optimized for Hungarian language analysis
- Large datasets may require significant processing time
- Results are saved incrementally to handle large-scale analysis
- The system automatically handles Hungarian-specific characters and diacritics

## 🔗 Related Projects

This project is part of the larger AI Content Machine workspace, focusing on linguistic analysis and content generation capabilities.

---

*For questions or contributions, please refer to the main project documentation.*
