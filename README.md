# Higher Education Disability ETL

ETL pipeline for analyzing the distribution of students with disabilities in Brazilian higher education, integrating Higher Education Census and SISU data into MongoDB.

## Project Structure

```
brazil-higher-education-disability-etl/
├── src/
│   ├── clients/                 # External service clients
│   │   ├── bigquery_client.py  # BigQuery client
│   │   └── mongodb_client.py   # MongoDB client
│   ├── config/                  # Configuration module
│   │   └── config.py           # Environment and settings
│   ├── etl/                     # ETL pipeline
│   │   └── pipeline.py         # Main ETL logic
│   └── utils/                   # Utilities
│       ├── logger.py           # Logging configuration
│       └── __init__.py
├── tests/                       # Test suite
│   └── test_etl.py            # ETL tests
├── logs/                        # Application logs
├── .env                         # Environment variables (not in git)
├── .gitignore                   # Git ignore rules
├── requirements.txt             # Python dependencies
├── main.py                      # Application entry point
├── pyproject.toml              # Project metadata
└── README.md                    # This file
```

## Getting Started

### Prerequisites
- Python 3.9+
- Google Cloud Project with BigQuery enabled
- MongoDB instance (local or cloud)
- Service account credentials from GCP

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd brazil-higher-education-disability-etl
```

2. **Create virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
Create a `.env` file in the root directory:
```env
GCP_PROJECT_ID=your-gcp-project-id
GCP_CREDENTIALS_PATH=path/to/credentials.json
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=higher_education
MONGO_COLLECTION=students
BIGQUERY_DATASET=your_dataset
BIGQUERY_TABLE=your_table
```

5. **Add Google Cloud credentials**
Place your service account JSON file (named `credentials.json`) in the root directory.

> **Security Note**: Add `credentials.json` to `.gitignore` - never commit credentials!

## Running the ETL

### Quick Start

1. **Ensure your `.env` file is configured** with all required variables
2. **Ensure MongoDB is running** (if using local instance)
3. **Run the ETL pipeline**:

```bash
python main.py
```

The pipeline will:
1. Extract data from BigQuery using your service account credentials
2. Transform the data (customize logic in `src/etl/pipeline.py`)
3. Load the data into MongoDB
4. Log all operations to `logs/etl_YYYYMMDD_HHMMSS.log`

### Output Example

```
2026-06-22 10:30:45,123 - src.utils.logger - INFO - Iniciando ETL pipeline...
2026-06-22 10:30:46,456 - src.etl.pipeline - INFO - Executando query: SELECT * FROM `dataset.table`
2026-06-22 10:30:50,789 - src.etl.pipeline - INFO - Dados extraídos: 1500 registros
2026-06-22 10:30:51,012 - src.etl.pipeline - INFO - Transformando dados...
2026-06-22 10:30:52,345 - src.etl.pipeline - INFO - Dados carregados: 1500 documentos inseridos
2026-06-22 10:30:52,567 - src.etl.pipeline - INFO - Pipeline finalizado com sucesso
```

### Troubleshooting

#### BigQuery Authentication Error
- Ensure `credentials.json` exists in the project root
- Verify the file path in `.env` matches the actual location
- Check that the service account has BigQuery permissions

#### MongoDB Connection Error
- Verify MongoDB is running: `mongosh` (or `mongo` for older versions)
- Check the `MONGO_URI` in `.env` matches your MongoDB instance
- Ensure network access to MongoDB (if using cloud instance)

#### Missing Environment Variables
- Verify all variables in `.env` are set
- Run `echo $VARIABLE_NAME` to check if variables are loaded
- Reload your shell: `source venv/bin/activate`

## Project Features

- Extracts data from BigQuery using service account authentication
- Transforms data with customizable logic
- Loads data into MongoDB
- Comprehensive logging
- Error handling and recovery
- Professional project structure
- Type hints and code quality tools

## Running Tests

### Run all tests with coverage

```bash
# Using pytest directly
python -m pytest tests/ -v --cov=src

# Or using tasks helper
python tasks.py tests
```

### Run specific test file

```bash
python -m pytest tests/test_etl.py -v
```

### Run with coverage report in HTML

```bash
python -m pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in your browser
```

## Development Tools

### Code Formatting

```bash
# Format code with black and isort
python tasks.py format

# Or individually:
python -m black src/ tests/ main.py
python -m isort src/ tests/ main.py
```

### Code Quality Checks

```bash
# Run linting
python tasks.py lint

# Or individually:
python -m flake8 src/ tests/ main.py
```

### Type Checking

```bash
# Check type hints
python tasks.py type-check

# Or individually:
python -m mypy src/
```

### Run all quality checks

```bash
python tasks.py format && python tasks.py lint && python tasks.py type-check
```

## Logging

Logs are stored in the `logs/` directory with timestamps. Check log files for detailed execution information.

## Configuration

Edit `src/config/config.py` or set environment variables to customize:
- BigQuery connection details
- MongoDB connection URI
- Database and collection names
- GCP project settings

## Dependencies

### Production
- `google-cloud-bigquery==3.14.1` - BigQuery client
- `pymongo==4.6.0` - MongoDB driver
- `python-dotenv==1.0.0` - Environment variable management

### Development
- `pytest` - Testing framework
- `black` - Code formatter
- `flake8` - Linter
- `isort` - Import sorter
- `mypy` - Type checker

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
