# Data Source

This project uses the New York City Taxi and Limousine Commission (TLC) Yellow Taxi Trip Record dataset.

- Official dataset page: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
- File used by the pipeline: `yellow_tripdata_2024-01.parquet`
- Direct source URL: https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet
- Data dictionary: https://www.nyc.gov/assets/tlc/downloads/pdf/data_dictionary_trip_records_yellow.pdf

The raw parquet file is not committed because it is large and reproducible. Running the analysis script downloads it into `data/raw/`.

The analysis filters the official records to realistic yellow-taxi trips and creates a modeling sample. The target variable is `long_trip`, defined as a trip duration of at least 30 minutes.
