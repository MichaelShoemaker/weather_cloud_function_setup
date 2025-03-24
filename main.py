import os
import requests
import dlt
import pandas as pd
from datetime import datetime, date, timezone
import functions_framework
from google.cloud import secretmanager
from zoneinfo import ZoneInfo

PROJECT_ID = "<Project-ID>"
BQ_DATASET = "weather_data"
BQ_TABLE = "hourly_weather"

def get_secret(secret_name: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    secret_path = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": secret_path})
    return response.payload.data.decode("UTF-8")

def fetch_weather_data():
    """Fetch hourly weather data from OpenWeather (One Call 3.0)."""
    API_KEY = get_secret("openweather-api-key")
    lat, lon = "41.881832", "-87.623177"  # Chicago
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&units=imperial&appid={API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch weather data: {response.text}")
    return response.json().get("hourly", [])

def transform_data(hourly_data):
    """Convert epoch to Chicago time, flatten record, add a stamp."""
    stamp = str(date.today())
    chicago_tz = ZoneInfo("America/Chicago")

    flat_data = []
    for record in hourly_data:
        # Convert from epoch -> UTC -> Chicago local time
        epoch_ts = record.get("dt", 0)
        utc_dt = datetime.fromtimestamp(epoch_ts, tz=timezone.utc)
        chicago_dt = utc_dt.astimezone(chicago_tz)

        flat_record = {
            "dt": record["dt"],  # Keep original UNIX timestamp for primary key
            "readable_dt": chicago_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),  # includes %Z for time zone
            "temp": record.get("temp"),
            "feels_like": record.get("feels_like"),
            "humidity": record.get("humidity"),
            "pressure": record.get("pressure"),
            "wind_speed": record.get("wind_speed"),
            "wind_deg": record.get("wind_deg"),
            "clouds": record.get("clouds"),
            "visibility": record.get("visibility"),
            "pop": record.get("pop"),
            "stamp": stamp
        }
        flat_data.append(flat_record)

    return flat_data

def load_data_to_bigquery(transformed_data):
    """Use DLT to load data into BigQuery, merging on dt so duplicates get overwritten."""
    pipeline = dlt.pipeline(
        pipeline_name="weather_pipeline",
        destination="bigquery",
        dataset_name=BQ_DATASET
    )
    pipeline.run(
        transformed_data,
        table_name=BQ_TABLE,
        write_disposition="merge",
        primary_key="dt"
    )

@functions_framework.http
def main(request):
    """Cloud Function Entry Point."""
    try:
        data = fetch_weather_data()
        transformed = transform_data(data)
        load_data_to_bigquery(transformed)
        return ("Hourly weather data loaded into BigQuery!", 200)
    except Exception as e:
        return (f"Error: {e}", 500)