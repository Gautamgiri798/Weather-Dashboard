🌦️ Weather Dashboard

Welcome to your personal, in-depth weather dashboard! This app transforms raw Open-Meteo data into a beautiful, interactive, and easy-to-read forecast for any city in the world.


✨ Features

This isn't just another weather app; it's a comprehensive data hub.

 Global City Search: 🌍 Find the weather for any location by name.
  
 Live Local Time: ⏰ The dashboard header shows the current date and time for the city you're viewing.
  
 Current Weather at-a-Glance: 🌡️ A modern 2x3 grid showing Temperature, "Feels Like," Humidity, Wind, Gusts, and today's max UV Index.
  
 Next 8 Hours: 🔜 A horizontal card-view forecast for the next 8 hours, showing temp, wind, and precipitation probability.
 
 Interactive Forecasts: 📈 Dynamic charts for hourly and daily trends.
 
 7-Day Outlook: 🗓️ A beautiful, modern card layout for the week ahead.
 
 In-Depth Soil Data: 🌱 Two dedicated charts showing hourly soil temperature and moisture at various depths.
  
 Raw Data Access: 🤓 Expandable sections to view the raw Pandas DataFrames.
  
  <details>
 <summary><strong>See Full List of Data Points</strong></summary>
  
 Current: Temp, Feels Like, Humidity, Wind, Gusts, UV Index, Weather Code
  
 Hourly: Temp, Apparent Temp, Precip. Probability, Wind Speed, Soil Temp (4 depths), Soil Moisture (5 depths)
  
 Daily: Max/Min Temp, Weather Code, Precip. Probability, Max Wind Speed
  
  </details>


🚀 How to Run This App

Get this dashboard running on your local machine in just 4 steps.

1. Get the Files

Download the following two files into a new project folder:

app.py

requirements.txt

2. Set Up Your Environment

It's highly recommended to use a virtual environment to keep your project dependencies clean.

# Create a new folder for your project
mkdir weather-dashboard
cd weather-dashboard
  
# Create a virtual environment (e.g., 'venv')
python -m venv venv
  
# Activate the environment
# On Windows:
.\venv\Scripts\Activate
# On macOS/Linux:
source venv/bin/activate

3. Install Dependencies

Install all the required Python libraries from the requirements.txt file.

pip install -r requirements.txt

4. Run the App!

Launch the Streamlit app. Streamlit will automatically open it in your default web browser.

streamlit run app.py


🛠️ Tech Stack

This app is built with a powerful, all-Python stack.

Streamlit: For the entire interactive web application framework.

Open-Meteo API: The source of all weather and geocoding data.

Plotly: For creating the beautiful, interactive charts.

Pandas: For all data manipulation and time-series handling.

Requests: For making API calls to the geocoding endpoint.


🤝 Credit

A huge thank you to Open-Meteo for providing an incredibly detailed, fast, and free-to-use weather API.
