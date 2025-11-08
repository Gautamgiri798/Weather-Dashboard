import openmeteo_requests
import requests_cache
import pandas as pd
import streamlit as st
import plotly.express as px
from retry_requests import retry
import requests  # Added for geocoding
import numpy as np # Keep numpy import, it's used by openmeteo client

# --- WMO Weather Code Mapping ---
# A more comprehensive map of WMO weather codes to descriptions and emojis
WMO_CODES = {
    0: "Clear sky ☀️",
    1: "Mainly clear 🌤️",
    2: "Partly cloudy 🌥️",
    3: "Overcast ☁️",
    45: "Fog 🌫️",
    48: "Depositing rime fog 🌫️",
    51: "Light drizzle 💧",
    53: "Moderate drizzle 💧",
    55: "Dense drizzle 💧",
    56: "Light freezing drizzle 🥶",
    57: "Dense freezing drizzle 🥶",
    61: "Slight rain 🌧️",
    63: "Moderate rain 🌧️",
    65: "Heavy rain 🌧️",
    66: "Light freezing rain 🥶",
    67: "Heavy freezing rain 🥶",
    71: "Slight snow fall 🌨️",
    73: "Moderate snow fall 🌨️",
    77: "Snow grains 🌨️",
    80: "Slight rain showers 🌦️",
    81: "Moderate rain showers 🌦️",
    82: "Violent rain showers 🌦️",
    85: "Slight snow showers 🌨️",
    86: "Heavy snow showers 🌨️",
    95: "Thunderstorm ⛈️",
    96: "Thunderstorm, slight hail ⛈️",
    99: "Thunderstorm, heavy hail ⛈️",
}

# --- Geocoding Function ---
@st.cache_data(ttl=3600)
def geocode_city(city_name):
    """
    (Name -> Coords) Uses the Open-Meteo Geocoding API to find coords for a city.
    Returns a dictionary with 'latitude', 'longitude', 'display_name', and 'timezone',
    or None if the city is not found.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {"name": city_name, "count": 1, "format": "json"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad status codes
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            
            # Construct a full display name
            display_name = result.get("name", "")
            admin1 = result.get("admin1", "")
            country = result.get("country", "")
            
            full_name_parts = [part for part in [display_name, admin1, country] if part]
            full_name = ", ".join(full_name_parts)
            
            return {
                "latitude": result["latitude"],
                "longitude": result["longitude"],
                "display_name": full_name,
                "timezone": result["timezone"]
            }
        else:
            return None
    except requests.RequestException as e:
        st.error(f"Geocoding API error: {e}")
        return None

# --- Weather API Client Class ---
class WeatherApiClient:
    """
    A class to fetch and process weather data from the Open-Meteo API.
    """
    def __init__(self, latitude, longitude):
        self.latitude = latitude
        self.longitude = longitude
        self.url = "https://api.open-meteo.com/v1/forecast"
        
        # Setup the Open-Meteo API client
        cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
        retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
        self.openmeteo = openmeteo_requests.Client(session=retry_session)

    def _get_params(self):
        """Returns the dictionary of parameters for the API call."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": "auto",
            "daily": [
                "weather_code", "temperature_2m_max", "temperature_2m_min", "apparent_temperature_max", 
                "apparent_temperature_min", "sunset", "sunrise", "precipitation_sum", 
                "precipitation_probability_max", "wind_speed_10m_max", "uv_index_max"
            ],
            "hourly": [
                "temperature_2m", "relative_humidity_2m", "weather_code", "pressure_msl", "surface_pressure", 
                "dew_point_2m", "precipitation", "precipitation_probability", "cloud_cover", 
                "visibility", "wind_speed_10m", "wind_gusts_10m", "apparent_temperature",
                "soil_temperature_0cm", "soil_temperature_6cm", "soil_temperature_18cm", "soil_temperature_54cm",
                "soil_moisture_0_to_1cm", "soil_moisture_1_to_3cm", "soil_moisture_3_to_9cm", 
                "soil_moisture_9_to_27cm", "soil_moisture_27_to_81cm"
            ],
            "current": [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature", "is_day", "precipitation", 
                "weather_code", "cloud_cover", "wind_speed_10m", "wind_gusts_10m", "uv_index"
            ],
        }

    def fetch_weather(self):
        """Fetches weather data from the API."""
        params = self._get_params()
        responses = self.openmeteo.weather_api(self.url, params=params)
        return responses[0], params

    def _process_location_data(self, response):
        """Extracts location metadata from the response."""
        
        # Decode bytes to string for timezone and abbreviation
        tz_bytes = response.Timezone()
        tz_abbrev_bytes = response.TimezoneAbbreviation()
        
        timezone_str = tz_bytes.decode('utf-8') if isinstance(tz_bytes, bytes) else tz_bytes
        timezone_abbrev_str = tz_abbrev_bytes.decode('utf-8') if isinstance(tz_abbrev_bytes, bytes) else tz_abbrev_bytes

        return {
            "latitude": response.Latitude(),
            "longitude": response.Longitude(),
            "elevation": response.Elevation(),
            "timezone": timezone_str,
            "timezone_abbreviation": timezone_abbrev_str
        }

    def _process_current_data(self, response, current_vars):
        """Processes the current weather data dynamically."""
        current = response.Current()
        current_data = {
            "time": pd.to_datetime(current.Time(), unit="s", utc=True)
        }
        for i, var in enumerate(current_vars):
            current_data[var] = current.Variables(i).Value()
        return current_data

    def _process_hourly_data(self, response, hourly_vars):
        """Processes the hourly forecast data dynamically."""
        hourly = response.Hourly()
        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        
        for i, var in enumerate(hourly_vars):
            hourly_data[var] = hourly.Variables(i).ValuesAsNumpy()
            
        return pd.DataFrame(data=hourly_data)

    def _process_daily_data(self, response, daily_vars):
        """Processes the daily forecast data dynamically."""
        daily = response.Daily()
        daily_data = {"date": pd.date_range(
            start=pd.to_datetime(daily.Time(), unit="s", utc=True),
            end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=daily.Interval()),
            inclusive="left"
        )}

        for i, var in enumerate(daily_vars):
            if var in ["sunrise", "sunset"]:
                daily_data[var] = daily.Variables(i).ValuesInt64AsNumpy()
            else:
                daily_data[var] = daily.Variables(i).ValuesAsNumpy()

        daily_dataframe = pd.DataFrame(data=daily_data)
        
        # Convert timestamp columns to datetime
        if "sunrise" in daily_dataframe:
            daily_dataframe["sunrise"] = pd.to_datetime(daily_dataframe["sunrise"], unit="s", utc=True)
        if "sunset" in daily_dataframe:
            daily_dataframe["sunset"] = pd.to_datetime(daily_dataframe["sunset"], unit="s", utc=True)
            
        return daily_dataframe

    def get_processed_data(self):
        """
        Fetches and processes all weather data.
        Returns:
            tuple: (location_info, current_data, hourly_dataframe, daily_dataframe)
        """
        response, params = self.fetch_weather()
        
        location_info = self._process_location_data(response)
        current_data = self._process_current_data(response, params["current"])
        hourly_df = self._process_hourly_data(response, params["hourly"])
        daily_df = self._process_daily_data(response, params["daily"])
        
        return location_info, current_data, hourly_df, daily_df

# --- Main Dashboard Function ---
def display_weather_dashboard(geo_info):
    """Renders the entire weather dashboard given geo_info."""
    try:
        with st.spinner(f"Fetching weather for {geo_info['display_name']}..."):
            client = WeatherApiClient(latitude=geo_info["latitude"], longitude=geo_info["longitude"])
            info, current, hourly_df, daily_df = client.get_processed_data()

        # 2. Display Location Info & Live Time
        st.header(f"Weather for {geo_info['display_name']}")
        
        # Get current time in local timezone
        current_time_local = current['time'].tz_convert(info['timezone'])
        st.subheader(f"Current Time: {current_time_local.strftime('%A, %B %d, %I:%M %p')}")
        
        st.caption(f"Coordinates: {info['latitude']:.4f}°N, {info['longitude']:.4f}°E | Elevation: {info['elevation']}m | Timezone: {info['timezone']} ({info['timezone_abbreviation']})")

        # 3. Display Current Weather (Revamped)
        st.header("Current Weather")
        weather_desc = WMO_CODES.get(int(current['weather_code']), "N/A")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Status", weather_desc)
        col2.metric("Temperature", f"{current['temperature_2m']:.1f} °C")
        col3.metric("Feels Like", f"{current['apparent_temperature']:.1f} °C")
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Humidity", f"{current['relative_humidity_2m']:.0f} %")
        col5.metric("Wind", f"{current['wind_speed_10m']:.1f} km/h", f"Gusts {current['wind_gusts_10m']:.1f} km/h")
        
        # Get today's max UV index from daily data (more reliable than current)
        today_uv_max = daily_df.iloc[0]['uv_index_max']
        col6.metric("UV Index", f"{today_uv_max:.1f}", help="Today's Max UV Index")

        # 4. NEW: Next 8 Hours Forecast
        st.header("Next 8 Hours")
        
        # Get current time in the location's timezone
        local_tz = info['timezone']
        now_local = pd.to_datetime('now', utc=True).tz_convert(local_tz)

        # Filter hourly data to start from the current hour
        hourly_df['date_local'] = hourly_df['date'].dt.tz_convert(local_tz)
        next_hours_df = hourly_df[hourly_df['date_local'] >= now_local].head(8)

        cols = st.columns(8)
        for i, (col, row) in enumerate(zip(cols, next_hours_df.itertuples())):
            with col.container(border=True):
                st.markdown(f"**{row.date_local.strftime('%I %p')}**") # 12-hour format
                icon = WMO_CODES.get(int(row.weather_code), "❓").split(" ")[0]
                st.markdown(f"<div style='font-size: 30px; text-align: center;'>{icon}</div>", unsafe_allow_html=True)
                st.metric("Temp", f"{row.temperature_2m:.0f}°")
                st.markdown(f"**{row.wind_speed_10m:.0f}** km/h")
                st.markdown(f"**{row.precipitation_probability:.0f}** %")

        # 5. Display Hourly Forecast Trend
        st.header("Hourly Forecast Trend")
        hourly_df_display = hourly_df[['date', 'temperature_2m', 'apparent_temperature', 'precipitation_probability', 'wind_speed_10m']]
        hourly_df_display = hourly_df_display.rename(columns={
            'temperature_2m': 'Temp (°C)', 'apparent_temperature': 'Feels Like (°C)',
            'precipitation_probability': 'Precip. Prob. (%)', 'wind_speed_10m': 'Wind (km/h)'
        })
        st.line_chart(hourly_df_display, x='date')
        
        # 6. Display Soil Data
        st.header("Hourly Soil Data")
        col_soil_1, col_soil_2 = st.columns(2)
        with col_soil_1:
            soil_temp_df = hourly_df[['date', 'soil_temperature_0cm', 'soil_temperature_6cm', 'soil_temperature_18cm', 'soil_temperature_54cm']]
            soil_temp_df = soil_temp_df.rename(columns={
                'soil_temperature_0cm': '0cm', 'soil_temperature_6cm': '6cm',
                'soil_temperature_18cm': '18cm', 'soil_temperature_54cm': '54cm'
            })
            fig_soil_temp = px.line(soil_temp_df, x='date', y=soil_temp_df.columns[1:],
                                    title="Hourly Soil Temperature (°C) at Depth", labels={'value': 'Temp (°C)', 'variable': 'Depth'})
            st.plotly_chart(fig_soil_temp, use_container_width=True)
        with col_soil_2:
            soil_moisture_df = hourly_df[['date', 'soil_moisture_0_to_1cm', 'soil_moisture_1_to_3cm', 'soil_moisture_3_to_9cm', 'soil_moisture_9_to_27cm', 'soil_moisture_27_to_81cm']]
            soil_moisture_df = soil_moisture_df.rename(columns={
                'soil_moisture_0_to_1cm': '0-1cm', 'soil_moisture_1_to_3cm': '1-3cm',
                'soil_moisture_3_to_9cm': '3-9cm', 'soil_moisture_9_to_27cm': '9-27cm', 'soil_moisture_27_to_81cm': '27-81cm'
            })
            fig_soil_moisture = px.line(soil_moisture_df, x='date', y=soil_moisture_df.columns[1:],
                                        title="Hourly Soil Moisture (m³/m³) at Depth", labels={'value': 'Moisture (m³/m³)', 'variable': 'Depth'})
            st.plotly_chart(fig_soil_moisture, use_container_width=True)

        # 7. Daily Forecast Section
        st.header("Daily Forecast")
        fig_daily_temp = px.line(daily_df, x='date', y=['temperature_2m_max', 'temperature_2m_min'],
                                 title="Daily Max/Min Temperature Trend", labels={'value': 'Temperature (°C)', 'variable': 'Metric'}, markers=True)
        fig_daily_temp.update_layout(legend_title_text='')
        st.plotly_chart(fig_daily_temp, use_container_width=True)
        st.subheader("7-Day Outlook")
        daily_df_display = daily_df.head(7).copy()
        daily_df_display['day_name'] = daily_df_display['date'].dt.tz_convert(info['timezone']).dt.strftime('%A')
        daily_df_display['date_str'] = daily_df_display['date'].dt.tz_convert(info['timezone']).dt.strftime('%b %d')
        daily_df_display['weather_desc'] = daily_df_display['weather_code'].map(WMO_CODES).fillna("N/A")
        daily_df_display['weather_icon'] = daily_df_display['weather_desc'].apply(lambda x: x.split(" ")[0])

        cols = st.columns(7)
        for i, (col, row) in enumerate(zip(cols, daily_df_display.itertuples())):
            with col.container(border=True):
                st.markdown(f"**{row.day_name}**", help=row.weather_desc)
                st.markdown(f"*{row.date_str}*")
                st.markdown(f"<div style='font-size: 42px; text-align: center;'>{row.weather_icon}</div>", unsafe_allow_html=True)
                st.metric("Temp", f"{row.temperature_2m_max:.0f}° / {row.temperature_2m_min:.0f}°")
                st.markdown(f"**Precip:** {row.precipitation_probability_max:.0f}%")
                st.markdown(f"**Wind:** {row.wind_speed_10m_max:.0f} km/h")

        # 8. Raw Data Expanders
        with st.expander("View Full Hourly Raw Data"): st.dataframe(hourly_df)
        with st.expander("View Full Daily Raw Data"): st.dataframe(daily_df)
            
    except Exception as e:
        st.error(f"An error occurred while fetching or processing weather data: {e}")
        st.exception(e)

# --- Streamlit App Logic ---
st.set_page_config(layout="wide")
st.title("Weather Dashboard 🌦️")

# --- Sidebar for Inputs ---
st.sidebar.header("📍 Location")
city_input = st.sidebar.text_input("Enter City Name", value="Amritsar")

if st.sidebar.button("Get Weather"):
    if not city_input:
        st.sidebar.error("Please enter a city name.")
    else:
        with st.spinner(f"Locating '{city_input}'..."):
            geo_info = geocode_city(city_input)
        
        if geo_info is None:
            st.error(f"Could not find city: '{city_input}'. Please check the spelling.")
        else:
            # If city is found, display the dashboard
            display_weather_dashboard(geo_info)
else:
    st.info("Enter a city name in the sidebar and click 'Get Weather' to load the dashboard.")