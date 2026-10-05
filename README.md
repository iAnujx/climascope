# ClimaScope

ClimaScope is a lightweight web dashboard for exploring climate and geospatial data stored in NetCDF (`.nc`) files. It combines a Flask API with an interactive browser interface for inspecting spatial distributions, time series, and anomalies.

## Features

- Upload NetCDF (`.nc`) datasets through the browser
- Automatically detect common latitude, longitude, time, and data-variable names
- Visualize gridded data as an interactive Plotly heatmap
- Select a map location and inspect its time series
- Animate available time steps
- Detect spatial anomalies using a configurable standard-deviation threshold
- Zoom to predefined geographic regions
- Search by latitude and longitude
- Export selected time-series data as CSV
- Compare two NetCDF datasets side by side
- Use the built-in guided tour and dashboard settings

## Technology Stack

### Backend

- Python
- Flask
- Flask-CORS
- xarray
- netCDF4
- NumPy
- Pandas
- SciPy

### Frontend

- HTML5
- Tailwind CSS
- JavaScript
- Plotly.js

The frontend does not require a JavaScript framework.

## Project Structure

```text
climascope/
├── app.py              # Flask application and API
├── index.html          # Web dashboard
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
└── .gitignore          # Git ignore rules
```

NetCDF files used for local testing are intentionally excluded from Git through `.gitignore`.

## Requirements

- Python 3.9 or later
- A modern browser such as Chrome, Edge, or Firefox
- A compatible NetCDF (`.nc`) dataset

## Installation

Clone the repository and enter the project directory:

```bash
git clone https://github.com/YOUR-USERNAME/climascope.git
cd climascope
```

Create a virtual environment:

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## Run Locally

Start the Flask application:

```bash
python app.py
```

Open the dashboard at:

```text
http://127.0.0.1:8080
```

The backend API is available under `/api/`. For example:

```text
http://127.0.0.1:8080/api/
```

The application can also be opened directly from `index.html` while the Flask server is running.

## Using ClimaScope

### 1. Upload a dataset

Select or drag a `.nc` file into the upload area. Files are processed by the Flask backend.

### 2. Select a variable

Choose one of the detected data variables. ClimaScope is designed for common gridded climate variables such as temperature, precipitation, wind, and pressure.

### 3. Explore the spatial data

The selected variable is displayed on an interactive Plotly map. You can zoom, pan, hover over values, and select locations.

### 4. Inspect a time series

Select a location on the map or enter latitude and longitude coordinates to retrieve the nearest available grid point and its time series.

### 5. Explore time steps

Use the time slider or animation controls to move through the available timesteps.

### 6. Analyze anomalies

Enable the anomaly overlay to identify values that exceed the configured standard-deviation threshold. The default threshold is ±2σ.

### 7. Export data

After selecting a location, export the resulting time series as a CSV file from the dashboard.

### 8. Compare datasets

Open comparison mode and upload a second NetCDF dataset. The dashboard can display both datasets side by side.

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/` | Check backend status |
| `POST` | `/api/upload` | Upload the primary NetCDF dataset |
| `GET` | `/api/heatmap?var=air&time=0` | Return 2D grid data for a selected variable and timestep |
| `GET` | `/api/timeseries?var=air&lat=28.6&lon=77.2` | Return the nearest grid-point time series |
| `GET` | `/api/anomaly?var=air&time=0` | Return anomaly information for a timestep |
| `POST` | `/api/upload2` | Upload a second dataset for comparison |
| `GET` | `/api/heatmap2?var=air&time=0` | Return heatmap data for the second dataset |

The exact variable and coordinate names depend on the uploaded NetCDF dataset.

## NetCDF Compatibility

ClimaScope attempts to identify common coordinate and variable naming conventions, including latitude, longitude, and time dimensions. It also filters common metadata variables such as bounds, masks, and vertex arrays when building the variable list.

Because NetCDF supports many different data structures, highly customized or non-gridded datasets may require preprocessing before visualization.

## Data Handling

Uploaded datasets are kept in the Flask application's runtime state for the current session. Restarting the application clears the loaded datasets, so they must be uploaded again.

The application accepts uploads up to 256 MB. For production deployments, additional validation, authentication, storage management, cleanup policies, and a production WSGI server should be configured.

## Sample Datasets

You can use publicly available NetCDF climate datasets from sources such as the NOAA Physical Sciences Laboratory.

- NCEP/NCAR Reanalysis: https://psl.noaa.gov/data/gridded/data.ncep.reanalysis.html

Dataset availability and download URLs may change. Refer to the provider's documentation for current data sources and usage terms.

## Troubleshooting

### Backend does not start

Check your Python installation:

```bash
python --version
```

Then reinstall the project dependencies if necessary:

```bash
pip install -r requirements.txt
```

### Browser cannot connect to the API

Make sure `app.py` is running and open:

```text
http://127.0.0.1:8080/api/
```

A successful response should report that the ClimaScope backend is running.

### NetCDF upload fails

Check that:

- The file uses the `.nc` extension.
- The dataset is a valid NetCDF file.
- The file is not corrupted.
- The dataset contains suitable spatial coordinates and at least one compatible data variable.
- The file is within the 256 MB upload limit.

### The map is empty

The dataset may use uncommon coordinate names, contain unsupported dimensions, or lack a suitable 2D spatial variable. You can inspect a dataset with xarray:

```python
import xarray as xr

ds = xr.open_dataset("your_file.nc")
print(ds)
```

## Development Checklist

Before pushing changes, verify:

- The application starts with `python app.py`.
- The dashboard loads at port 8080.
- NetCDF upload works.
- Variables are detected correctly.
- The heatmap renders.
- Location selection produces a time series.
- CSV export works.
- Anomaly detection works.
- Dataset comparison works.
- No local datasets, credentials, or temporary files are committed.

## Deployment Notes

For production deployment:

1. Use a production WSGI server instead of Flask's development server.
2. Restrict CORS to trusted frontend origins.
3. Keep upload limits and file validation enabled.
4. Use appropriate storage and cleanup policies for uploaded datasets.
5. Add authentication if the application is exposed to untrusted users.
6. Keep Python dependencies updated.
7. Avoid committing large climate datasets or private data to Git.

## License

This project is released under the MIT License. See `LICENSE` for the full license text.
