from pathlib import Path
import pandas as pd


INPUT_DIR = Path("data/raw")
OUTPUT_DIR = Path("data/parquet")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def normalize_column_name(column: str) -> str:
    return (
        column.strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
        .replace(".", "_")
    )


def convert_csv_to_parquet(input_file: Path) -> None:
    output_file = OUTPUT_DIR / f"{input_file.stem}.parquet"

    print(f"Lendo arquivo: {input_file}")

    df = pd.read_csv(
        input_file,
        sep=";",
        encoding="latin1",
        low_memory=False
    )

    df.columns = [normalize_column_name(col) for col in df.columns]

    print(f"Linhas: {len(df)}")
    print(f"Colunas: {len(df.columns)}")

    df.to_parquet(
        output_file,
        engine="pyarrow",
        index=False
    )

    print(f"Arquivo Parquet gerado: {output_file}")
    print("-" * 80)


def main() -> None:
    csv_files = sorted([
        file for file in INPUT_DIR.iterdir()
        if file.is_file() and file.suffix.lower() == ".csv"
    ])

    if not csv_files:
        print(f"Nenhum arquivo CSV encontrado em: {INPUT_DIR}")
        return

    print(f"Arquivos CSV encontrados: {len(csv_files)}")
    print("-" * 80)

    for csv_file in csv_files:
        convert_csv_to_parquet(csv_file)


if __name__ == "__main__":
    main()