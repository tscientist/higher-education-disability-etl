# Quick Start Guide

## Installation

### Prerequisites

- Python 3.9+
- Google Cloud SDK credentials (see `SETUP_BIGQUERY.md`)
- MongoDB 4.0+ (local or cloud)
- Virtual environment (recommended)

### Setup

1. **Clone and navigate to project:**

```bash
cd /path/to/brazil-higher-education-disability-etl
```

2. **Create virtual environment:**

```bash
python -m venv venv
source venv/bin/activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
# Or for development:
pip install -e ".[dev]"
```

4. **Configure environment variables:**

Create or update `.env` file:

```env
# Google Cloud
GCP_PROJECT_ID=higher-education-disability
GCP_CREDENTIALS_PATH=credentials.json

# MongoDB
MONGO_URI=mongodb://localhost:27017
MONGO_DATABASE=higher_education

# ETL Configuration
ETL_START_YEAR=2018
ETL_END_YEAR=2022
# ETL_LIMIT=1000  # Uncomment for testing with limited rows

# BigQuery
BIGQUERY_DATASET=ppgti_etl_test
```

5. **Verify BigQuery staging tables exist:**

```bash
python scripts/verify_bigquery_tables.py
```

## Running the Pipeline

### Batch-Corrected Mode 

```bash
python main.py --mode batch-corrected
```

**What it does:**
- Loads SISU aggregated data (1x): 3.5M → ~150k documents
- Loads CENSO IES (1x): ~2,600 institutions (stays in memory!)
- Processes CENSO CURSO in 29 batches (20k per batch)
- Joins with O(1) lookups against indices
- Completes in ~8-10 minutes

**Why it's fast:** IES is always small, allowing complete in-memory indices and O(1) joins!

### With Advanced MongoDB Queries

Run ETL + 8 advanced aggregation pipeline queries:

```bash
python main.py --mode with-queries
```

Includes complex queries with `$lookup`, `$group`, `$facet`, `$unwind`, etc.

### Full Pipeline (All Data at Once)

Executes all 8 phases plus validation:

```bash
python main.py
```

Or with explicit mode:

```bash
python main.py --mode full
```

**What it does:**
- ✓ Extracts data from BigQuery
- ✓ Transforms and joins Census data
- ✓ Transforms SISU data into aggregations
- ✓ Builds final analytical documents
- ✓ Loads documents into MongoDB
- ✓ Creates indexes for queries
- ✓ Validates results and displays sample

**Output:**
- Console logs (streaming)
- File logs: `logs/etl_YYYYMMDD_HHMMSS.log`

### Phase-Based Execution (For Testing)

**Extract only (Phase 1):**

```bash
python main.py --mode extract
```

Use case: Verify BigQuery connectivity and staging data exists

**Extract through Build (Phases 1-6):**

```bash
python main.py --mode build
```

Use case: Test transformations without MongoDB I/O

### Python API Usage

```python
from src.etl.pipeline_orchestrator import ETLPipelineOrchestrator

# Create orchestrator
orchestrator = ETLPipelineOrchestrator()

# Run full pipeline
result = orchestrator.run_full_pipeline()

# Or individual phases
phase1_result = orchestrator.run_phase_1_extract()
```

## Testing MongoDB Queries

### Run Query Examples

Demonstrates find queries, aggregations, and lookups:

```bash
python scripts/mongodb_query_examples.py
```

### Query Examples Include

1. **Simple filters** - Filter by year, UF, modality
2. **Dot notation** - Access nested fields (IES, course, metrics)
3. **Array access** - Query SISU demographics with $elemMatch
4. **Aggregations** - Answer 8+ analytical questions:
   - Evolution of PcD enrollments by year
   - PcD concentration by region
   - Completion rates by category
   - SISU access funnel
   - And more...

### Performance Analysis

Check index efficiency:

```bash
python scripts/mongodb_explain_plan.py
```

This shows:
- Index usage (IXSCAN vs COLLSCAN)
- Query execution times
- Documents examined
- Performance recommendations

## MongoDB Collections

After running the pipeline, you'll have:

### `gold_course_indicators`

Main analytical collection with one document per course per year per institution.

**Query examples:**

```javascript
// Find all courses in SP in 2022
db.gold_course_indicators.find({
  ano: 2022,
  uf: "SP"
})

// Find high PcD enrollment courses
db.gold_course_indicators.find({
  "metricasCalculadas.percentualMatriculasPcd": { $gt: 10 }
})

// Group PcD enrollments by UF
db.gold_course_indicators.aggregate([
  { $group: {
      _id: "$uf",
      totalPcd: { $sum: "$indicadoresDeficiencia.matriculas" }
  }},
  { $sort: { totalPcd: -1 }}
])
```

### `sisu_aggregated`

SISU data aggregated by course/institution/year with demographic breakdowns.

```javascript
// Find SISU data for a specific course
db.sisu_aggregated.findOne({
  idIes: "634",
  idCurso: "15002"
})
```

## Data Schema

### Course Year IDs

Document ID format: `{ano}_{id_ies}_{id_curso}`

Example: `2022_634_15002`
- Year: 2022
- Institution: 634 (UFPEL)
- Course: 15002 (Computer Science)

### Key Fields

```javascript
{
  ano: 2022,                    // Year
  uf: "RS",                     // State
  ies: {                        // Institution
    idIes: "634",
    nome: "UNIVERSIDADE FEDERAL DE PELOTAS",
    sigla: "UFPEL"
  },
  curso: {                      // Course
    idCurso: "15002",
    nome: "Ciência Da Computação",
    tipoModalidadeEnsino: "1"   // 1=Presencial, 2=EAD
  },
  
  // Student indicators
  indicadoresAluno: {
    matriculas: 377,            // Total enrolled
    ingressantes: 92,           // New entrants
    concluintes: 32             // Graduates
  },
  
  // PcD indicators
  indicadoresDeficiencia: {
    matriculas: 8,              // PcD enrolled
    ingressantes: 4,            // PcD new entrants
    concluintes: 1              // PcD graduates
  },
  
  // Computed metrics
  metricasCalculadas: {
    percentualMatriculasPcd: 2.12,      // % of enrollments
    taxaConclusaoGeral: 34.78,          // General completion rate
    taxaConclusaoPcd: 25.0,             // PcD completion rate
    taxaPerdaGeral: 65.22,              // General loss rate
    taxaPerdaPcd: 75.0                  // PcD loss rate
  },
  
  // SISU data (if available)
  sisu: {
    hasMatch: true,
    inscricoesTotal: 123,               // Total SISU applications
    inscricoesPcd: 10,                  // PcD applications
    aprovadosPcdRegular: 2,             // PcD approved
    matriculadosPcdFinal: 1,            // PcD enrolled
    notaCandidatoMediaPcd: 650.2,       // Avg grade PcD
    demografia: {
      porSexo: [ /* breakdown by sex */ ],
      porFaixaEtaria: [ /* by age group */ ],
      porMunicipio: [ /* by hometown */ ]
    }
  }
}
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| GCP_PROJECT_ID | higher-education-disability | GCP project ID |
| GCP_CREDENTIALS_PATH | credentials.json | Path to service account JSON |
| BIGQUERY_DATASET | ppgti_etl_test | BigQuery dataset name |
| ETL_START_YEAR | 2018 | First year to extract |
| ETL_END_YEAR | 2022 | Last year to extract |
| ETL_LIMIT | (none) | Row limit per table for testing |
| MONGO_URI | mongodb://localhost:27017 | MongoDB connection |
| MONGO_DATABASE | higher_education | MongoDB database |

### Using ETL_LIMIT for Testing

When developing or testing, limit rows processed:

```bash
ETL_LIMIT=100 python main.py --mode build
```

This processes only 100 rows per BigQuery table, useful for:
- Verifying pipeline logic
- Testing MongoDB connection
- Performance testing without full data load

## Troubleshooting

### "Not found: Dataset..."

**Problem:** BigQuery staging tables not found

**Solution:**
1. Verify BigQuery dataset exists: `SETUP_BIGQUERY.md`
2. Check GCP_PROJECT_ID and BIGQUERY_DATASET
3. Verify credentials have BigQuery access

### "Cannot connect to MongoDB"

**Problem:** MongoDB connection failed

**Solution:**
1. Check MONGO_URI is correct
2. Verify MongoDB is running: `mongodb://localhost:27017`
3. For cloud MongoDB, check IP whitelist
4. Verify network connectivity

### Memory or timeout issues

**Problem:** Pipeline runs out of memory or times out

**Solution:**
1. Use ETL_LIMIT for testing: `ETL_LIMIT=1000 python main.py`
2. Split by year: `ETL_START_YEAR=2022 ETL_END_YEAR=2022`
3. Increase BigQuery timeout in code if needed
4. Check system resources

### Schema mismatches in BigQuery

**Problem:** "Field X not found" errors

**Solution:**
1. Phase logs will warn about missing columns
2. Affected indicators are skipped
3. Pipeline continues with available data
4. Check `stg_censo_curso` schema matches documentation

## Performance Tips

### Index Strategy

After first run, indexes are created automatically in Phase 8.

Verify they exist:

```bash
python -c "from pymongo import MongoClient; m = MongoClient('mongodb://localhost:27017'); \
  print(m['higher_education']['gold_course_indicators'].list_indexes())"
```

### Query Tips

1. **Always filter by year** (most selective):
   ```javascript
   db.gold_course_indicators.find({ ano: 2022, ... })
   ```

2. **Use projection** to limit returned fields:
   ```javascript
   find(filter, { _id: 1, "ies.nome": 1, "curso.nome": 1 })
   ```

3. **For aggregations**, use `$match` early:
   ```javascript
   aggregate([ 
     { $match: { ano: 2022 } },  // Filter first
     { $group: { ... } }         // Then aggregate
   ])
   ```

## Next Steps

1. **Explore data:** Use query examples to understand the data
2. **Build dashboards:** Use MongoDB data in BI tools (PowerBI, Metabase, etc.)
3. **Create alerts:** Monitor PcD enrollment trends
4. **Academic analysis:** Publish findings on access and permanence

## Support & Documentation

- **Architecture:** `docs/ETL_ARCHITECTURE.md`
- **Query examples:** `scripts/mongodb_query_examples.py`
- **Performance tuning:** `scripts/mongodb_explain_plan.py`
- **BigQuery setup:** `SETUP_BIGQUERY.md`
- **Logs:** `logs/etl_*.log`

## License

MIT License - See LICENSE file for details
