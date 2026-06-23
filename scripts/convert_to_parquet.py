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
    )


def convert_csv_to_parquet(input_file: Path, output_file: Path) -> None:
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

    print(f"Arquivo gerado: {output_file}")


def main():
    files = [
        "microdados_ed_sup_ies_2024.csv",
        "microdados_cadastro_cursos_2024.csv",
    ]

    for file_name in files:
        input_file = INPUT_DIR / file_name
        output_file = OUTPUT_DIR / file_name.replace(".csv", ".parquet")

        convert_csv_to_parquet(input_file, output_file)


if __name__ == "__main__":
    main()