import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

st.set_page_config(page_title="Village Radius Finder", layout="wide")

st.title("🗺️ 10 km Village Radius Automation Tool")
st.write("Find all surrounding settlements within a precise 10 km radius using OpenStreetMap data.")

# Input Mode Selection
input_mode = st.radio("Choose Input Method:", ["Search by Village Name", "Enter Coordinates Directly (Recommended for small villages)"])

center_lat, center_lon = None, None
target_village = "Target Location"
radius_km = st.number_input("Radius (km)", min_value=1, max_value=50, value=10)

if input_mode == "Search by Village Name":
    col1, col2 = st.columns(2)
    with col1:
        target_village = st.text_input("Target Village Name", "Nimbawade")
    with col2:
        region_hint = st.text_input("Region / State / Country", "Atpadi, Sangli, Maharashtra, India")
    
    if st.button("Find Location & Scan Radius", type="primary"):
        geo_query = f"{target_village}, {region_hint}"
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': geo_query, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'VillageRadiusApp/1.0'}
        
        response = requests.get(url, params=params, headers=headers).json()
        if response:
            center_lat = float(response[0]['lat'])
            center_lon = float(response[0]['lon'])
            st.success(f"Located! Lat: {center_lat}, Lon: {center_lon}")
        else:
            st.error("Could not find exact coordinates via text search. Try switching to 'Enter Coordinates Directly' above!")

else:
    col1, col2, col3 = st.columns(3)
    with col1:
        target_village = st.text_input("Village Name", "Nimbawade")
    with col2:
        center_lat = st.number_input("Latitude", value=17.45, format="%.5f")
    with col3:
        center_lon = st.number_input("Longitude", value=74.78, format="%.5f")
    
    if st.button("Scan Radius from Coordinates", type="primary"):
        pass

# Run Overpass Scan if Coordinates are Available
if center_lat and center_lon:
    with st.spinner("Scanning OpenStreetMap for surrounding villages within 10 km..."):
        overpass_url = "http://overpass-api.de/api/interpreter"
        radius_meters = radius_km * 1000
        query = f"""
        [out:json][timeout:25];
        (
          node["place"~"village|hamlet"](around:{radius_meters},{center_lat},{center_lon});
          way["place"~"village|hamlet"](around:{radius_meters},{center_lat},{center_lon});
          relation["place"~"village|hamlet"](around:{radius_meters},{center_lat},{center_lon});
        );
        out center;
        """
        op_response = requests.post(overpass_url, data={'data': query}).json()
        elements = op_response.get('elements', [])
        
        villages_data = []
        center_coords = (center_lat, center_lon)
        
        for el in elements:
            lat = el.get('lat') or (el.get('center', {})).get('lat')
            lon = el.get('lon') or (el.get('center', {})).get('lon')
            
            if lat and lon:
                name = el.get('tags', {}).get('name', 'Unnamed Village/Hamlet')
                place_type = el.get('tags', {}).get('place', 'village')
                dist_km = round(geodesic(center_coords, (lat, lon)).km, 2)
                
                if dist_km <= radius_km:
                    villages_data.append({
                        'Village Name': name,
                        'Type': place_type,
                        'Distance (km)': dist_km,
                        'Latitude': lat,
                        'Longitude': lon
                    })
        
        df = pd.DataFrame(villages_data)
        
        if df.empty:
            st.warning(f"No villages found within {radius_km} km in OpenStreetMap for these coordinates.")
        else:
            df = df.sort_values(by='Distance (km)').reset_index(drop=True)
            st.success(f"Found {len(df)} settlements within {radius_km} km!")
            
            st.subheader("📊 Results Table")
            st.dataframe(df[['Village Name', 'Type', 'Distance (km)']], use_container_width=True)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Village List as CSV", data=csv, file_name=f"{target_village}_villages.csv", mime="text/csv")
            
            st.subheader("🗺️ Visual Map Confirmation")
            st.info("Blue circle = exact 10 km radius boundary. Red pin = your center village; Green pins = surrounding verified settlements.")
            
            m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
            folium.Marker([center_lat, center_lon], popup=f"<b>Center: {target_village}</b>", icon=folium.Icon(color='red', icon='home')).add_to(m)
            folium.Circle(radius=radius_meters, location=[center_lat, center_lon], color='blue', fill=True, fill_opacity=0.1).add_to(m)
            
            for _, row in df.iterrows():
                if row['Village Name'] != target_village:
                    folium.Marker(
                        [row['Latitude'], row['Longitude']],
                        popup=f"<b>{row['Village Name']}</b><br>Dist: {row['Distance (km)']} km",
                        icon=folium.Icon(color='green', icon='info-sign')
                    ).add_to(m)
            
            st_folium(m, width=700, height=500)
