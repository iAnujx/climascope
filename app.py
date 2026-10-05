from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, tempfile
import numpy as np

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 256 * 1024 * 1024

loaded_datasets = {}

def safe_json(arr):
    arr = np.array(arr, dtype=float)
    arr = np.where(np.isnan(arr), None, arr)
    arr = np.where(arr == np.inf, None, arr)
    arr = np.where(arr == -np.inf, None, arr)
    return arr.tolist()

def find_dim(ds, dim_type):
    patterns = {
        'lat':  ['lat', 'latitude', 'y', 'nav_lat', 'yt_ocean', 'geolat', 'ylat', 'lats'],
        'lon':  ['lon', 'longitude', 'x', 'nav_lon', 'xt_ocean', 'geolon', 'long', 'lons'],
        'time': ['time', 't', 'month', 'day', 'year', 'hours', 'datetime'],
    }
    candidates = patterns.get(dim_type, [dim_type])
    all_keys = list(ds.sizes) + list(ds.coords)
    for key in all_keys:
        for c in candidates:
            if c.lower() == key.lower():
                return key
    for key in all_keys:
        for c in candidates:
            if c.lower() in key.lower():
                return key
    return None

def find_var(ds, hint=None):
    vars_list = list(ds.data_vars)
    if not vars_list:
        return None
    if hint and hint in ds.data_vars:
        return hint
    if hint:
        patterns = {
            'temperature': ['air', 'temp', 't2m', 'tas', 'tmp', 'skt', 'tmax', 'tmin'],
            'precipitation': ['prate', 'precip', 'pr', 'rain', 'tp', 'prcp'],
            'wind': ['uwnd', 'vwnd', 'u10', 'v10', 'wspd', 'wind'],
            'pressure': ['slp', 'psl', 'msl', 'press', 'sp', 'pres', 'pmsl'],
            'humidity': ['rhum', 'shum', 'hum', 'rh', 'q'],
        }
        hint_lower = hint.lower()
        candidates = []
        for key, vals in patterns.items():
            if hint_lower == key or hint_lower in vals:
                candidates = vals
                break
        if not candidates:
            candidates = [hint_lower]
        for var in vars_list:
            for c in candidates:
                if c.lower() in var.lower() or var.lower() in c.lower():
                    return var
    return vars_list[0]

def is_data_var(ds, var):
    da = ds[var]
    if da.ndim < 2:
        return False
    skip_patterns = ['bounds', 'bnds', 'nbnds', 'climatology', 'time_bnds', 'lat_bnds', 'lon_bnds', 'area', 'mask', 'vertices', 'edges', 'nbnd']
    var_lower = var.lower()
    for pattern in skip_patterns:
        if pattern in var_lower:
            return False
    return True

def extract_2d(da, lat_dim, lon_dim, time_dim, time_idx):
    try:
        dims = list(da.dims)
        if time_dim and time_dim in dims:
            n = da.sizes[time_dim]
            time_idx = max(0, min(time_idx, n - 1))
            da = da.isel({time_dim: time_idx})
        da = da.squeeze()
        dims = list(da.dims)
        if lat_dim and lon_dim and lat_dim in dims and lon_dim in dims:
            da = da.transpose(lat_dim, lon_dim)
        elif len(dims) > 2:
            for extra in dims:
                if extra not in [lat_dim, lon_dim]:
                    da = da.isel({extra: 0})
            da = da.squeeze()
        return da.values
    except Exception as e:
        return da.squeeze().values

@app.route('/')
def home():
    return send_from_directory(os.path.dirname(__file__), 'index.html')

@app.route('/api/')
def api_home():
    return jsonify({"status": "running", "message": "ClimaScope backend is live!"})

@app.route('/api/upload', methods=['POST'])
def upload():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files['file']
        if not file.filename.lower().endswith('.nc'):
            return jsonify({"error": "Must be a .nc NetCDF file"}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
        file.save(tmp.name)
        tmp.close()
        import xarray as xr
        ds = xr.open_dataset(tmp.name, decode_times=False)
        loaded_datasets['current'] = ds
        loaded_datasets['path'] = tmp.name
        time_dim = find_dim(ds, 'time')
        lat_dim  = find_dim(ds, 'lat')
        lon_dim  = find_dim(ds, 'lon')
        n_times = int(ds.sizes[time_dim]) if time_dim and time_dim in ds.sizes else 1
        lat_range = [float(ds[lat_dim].min()), float(ds[lat_dim].max())] if lat_dim else [0, 0]
        lon_range = [float(ds[lon_dim].min()), float(ds[lon_dim].max())] if lon_dim else [0, 0]
        variables = [v for v in ds.data_vars.keys() if is_data_var(ds, v)]
        if not variables:
            variables = list(ds.data_vars.keys())
        variable_labels = {v: v for v in variables}
        return jsonify({
            "success": True, "filename": file.filename,
            "variables": variables, "variable_labels": variable_labels,
            "n_timesteps": n_times, "lat_range": lat_range,
            "lon_range": lon_range,
            "dimensions": {k: int(v) for k, v in ds.sizes.items()}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/heatmap')
def heatmap():
    try:
        if 'current' not in loaded_datasets:
            return jsonify({"error": "No file uploaded yet"}), 400
        ds = loaded_datasets['current']
        var_hint = request.args.get('var', '')
        time_idx = int(request.args.get('time', 0))
        var_name = find_var(ds, var_hint)
        da = ds[var_name]
        lat_dim = find_dim(ds, 'lat')
        lon_dim = find_dim(ds, 'lon')
        time_dim = find_dim(ds, 'time')
        values = extract_2d(da, lat_dim, lon_dim, time_dim, time_idx)
        lats = ds[lat_dim].values.tolist() if lat_dim else list(range(values.shape[0]))
        lons = ds[lon_dim].values.tolist() if lon_dim else list(range(values.shape[1]))
        flat = values.astype(float).flatten()
        flat = flat[np.isfinite(flat)]
        vmin = float(np.percentile(flat, 2)) if len(flat) > 0 else 0
        vmax = float(np.percentile(flat, 98)) if len(flat) > 0 else 1
        return jsonify({
            "variable": var_name, "timestep": time_idx,
            "lats": lats, "lons": lons, "values": safe_json(values),
            "vmin": vmin, "vmax": vmax,
            "units": str(da.attrs.get('units', ''))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/timeseries')
def timeseries():
    try:
        if 'current' not in loaded_datasets:
            return jsonify({"error": "No file uploaded yet"}), 400
        ds = loaded_datasets['current']
        var_hint  = request.args.get('var', '')
        lat_query = float(request.args.get('lat', 0))
        lon_query = float(request.args.get('lon', 0))
        var_name  = find_var(ds, var_hint)
        da        = ds[var_name]
        lat_dim   = find_dim(ds, 'lat')
        lon_dim   = find_dim(ds, 'lon')
        time_dim  = find_dim(ds, 'time')
        lat_idx = int(np.abs(ds[lat_dim].values - lat_query).argmin()) if lat_dim else 0
        lon_idx = int(np.abs(ds[lon_dim].values - lon_query).argmin()) if lon_dim else 0
        sel = {}
        if lat_dim and lat_dim in da.dims: sel[lat_dim] = lat_idx
        if lon_dim and lon_dim in da.dims: sel[lon_dim] = lon_idx
        for dim in list(da.dims):
            if dim not in sel and dim != time_dim: sel[dim] = 0
        series = da.isel(sel)
        values = series.values.flatten()
        time_labels = list(range(len(values)))
        if time_dim and time_dim in ds.coords:
            try: time_labels = [str(t) for t in ds[time_dim].values]
            except: pass
        actual_lat = float(ds[lat_dim].values[lat_idx]) if lat_dim else lat_query
        actual_lon = float(ds[lon_dim].values[lon_idx]) if lon_dim else lon_query
        return jsonify({
            "variable": var_name, "lat": actual_lat, "lon": actual_lon,
            "times": time_labels, "values": safe_json(values),
            "units": str(da.attrs.get('units', ''))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/anomaly')
def anomaly():
    try:
        if 'current' not in loaded_datasets:
            return jsonify({"error": "No file uploaded yet"}), 400
        ds = loaded_datasets['current']
        var_hint = request.args.get('var', '')
        time_idx = int(request.args.get('time', 0))
        var_name = find_var(ds, var_hint)
        da = ds[var_name]
        lat_dim = find_dim(ds, 'lat')
        lon_dim = find_dim(ds, 'lon')
        time_dim = find_dim(ds, 'time')
        values = extract_2d(da, lat_dim, lon_dim, time_dim, time_idx)
        mean = np.nanmean(values)
        std  = np.nanstd(values)
        mask  = (np.abs(values - mean) > 2 * std).astype(float)
        mask  = np.where(np.isnan(values.astype(float)), None, mask)
        sigma = np.abs(values - mean) / (std + 1e-10)
        return jsonify({
            "variable": var_name, "timestep": time_idx,
            "mean": float(mean), "std": float(std),
            "anomaly_mask": safe_json(mask),
            "sigma_distance": safe_json(sigma)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload2', methods=['POST'])
def upload2():
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        file = request.files['file']
        if not file.filename.lower().endswith('.nc'):
            return jsonify({"error": "Must be a .nc NetCDF file"}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.nc')
        file.save(tmp.name)
        tmp.close()
        import xarray as xr
        ds = xr.open_dataset(tmp.name, decode_times=False)
        loaded_datasets['second'] = ds
        loaded_datasets['second_path'] = tmp.name
        variables = [v for v in ds.data_vars.keys() if is_data_var(ds, v)]
        if not variables: variables = list(ds.data_vars.keys())
        time_dim = find_dim(ds, 'time')
        lat_dim  = find_dim(ds, 'lat')
        lon_dim  = find_dim(ds, 'lon')
        n_times = int(ds.sizes[time_dim]) if time_dim and time_dim in ds.sizes else 1
        lat_range = [float(ds[lat_dim].min()), float(ds[lat_dim].max())] if lat_dim else [0,0]
        lon_range = [float(ds[lon_dim].min()), float(ds[lon_dim].max())] if lon_dim else [0,0]
        return jsonify({
            "success": True, "filename": file.filename,
            "variables": variables, "variable_labels": {v:v for v in variables},
            "n_timesteps": n_times, "lat_range": lat_range, "lon_range": lon_range
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/heatmap2')
def heatmap2():
    try:
        if 'second' not in loaded_datasets:
            return jsonify({"error": "No second file uploaded"}), 400
        ds = loaded_datasets['second']
        var_hint = request.args.get('var', '')
        time_idx = int(request.args.get('time', 0))
        var_name = find_var(ds, var_hint)
        da = ds[var_name]
        lat_dim  = find_dim(ds, 'lat')
        lon_dim  = find_dim(ds, 'lon')
        time_dim = find_dim(ds, 'time')
        values   = extract_2d(da, lat_dim, lon_dim, time_dim, time_idx)
        lats = ds[lat_dim].values.tolist() if lat_dim else list(range(values.shape[0]))
        lons = ds[lon_dim].values.tolist() if lon_dim else list(range(values.shape[1]))
        flat = values.astype(float).flatten()
        flat = flat[np.isfinite(flat)]
        vmin = float(np.percentile(flat, 2)) if len(flat) > 0 else 0
        vmax = float(np.percentile(flat, 98)) if len(flat) > 0 else 1
        return jsonify({
            "variable": var_name, "timestep": time_idx,
            "lats": lats, "lons": lons, "values": safe_json(values),
            "vmin": vmin, "vmax": vmax,
            "units": str(da.attrs.get('units', ''))
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
