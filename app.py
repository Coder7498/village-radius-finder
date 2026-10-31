import streamlit as st
import requests
import pandas as pd
import folium
from streamlit_folium import st_folium
from geopy.distance import geodesic

st.set_page_config(page_title="Village Radius Finder", layout="wide")

st.title("🗺️ 10 km Village Radius Automation Tool")
st.write("Enter any village name and region to instantly find all surrounding settlements within a precise 10 km radius, complete with distance calculations and map verification.")

col1, col2, col3 = st.columns(3)
with col1:
    target_village = st.text_input("Target Village Name", "Rampur")
with col2:
    region_hint = st.text_input("Region / State / Country", "Uttar Pradesh, India")
with col3:
    radius_km = st.number_input("Radius (km)", min_value=1, max_value=50, value=10)

if st.button("Find Villages & Verify Map", type="primary"):
    with st.spinner("Scanning OpenStreetMap and calculating exact geodesic distances..."):
        
        geo_query = f"{target_village}, {region_hint}" if region_hint else target_village
        url = "https://nominatim.openstreetmap.org/search"
        params = {'q': geo_query, 'format': 'json', 'limit': 1}
        headers = {'User-Agent': 'VillageRadiusApp/1.0'}
        
        response = requests.get(url, params=params, headers=headers).json()
        
        if not response:
            st.error("Village not found! Please check the spelling or add a broader region hint.")
        else:
            center_lat = float(response[0]['lat'])
            center_lon = float(response[0]['lon'])
            
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
                st.warning(f"No villages found within {radius_km} km of {target_village}.")
            else:
                df = df.sort_values(by='Distance (km)').reset_index(drop=True)
                st.success(f"Found {len(df)} settlements within {radius_km} km!")
                
                st.subheader("📊 Results Table")
                st.dataframe(df[['Village Name', 'Type', 'Distance (km)']], use_container_width=True)
                
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Village List as CSV", data=csv, file_name=f"{target_village}_villages.csv", mime="text/csv")
                
                st.subheader("🗺️ Visual Map Confirmation")
                st.info("The blue circle marks the exact boundary. Red pin is your target village; green pins are the verified surrounding settlements.")
                
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
                
                st_data = st_folium(m, width=700, height=500)
