import ast
import streamlit as st
import leafmap.foliumap as leafmap
import pandas as pd
import shapely.geometry
import numpy as np
from bs4 import BeautifulSoup
import json, re, requests
import streamlit_analytics

url = 'https://www.rightmove.co.uk/property-for-sale/find.html?searchType=SALE&locationIdentifier=REGION%5E1290&insId=1&radius=0.0&minPrice=&maxPrice=325000&minBedrooms=&maxBedrooms=3&displayPropertyType=&maxDaysSinceAdded=&_includeSSTC=on&sortByPriceDescending=&primaryDisplayPropertyType=&secondaryDisplayPropertyType=&oldDisplayPropertyType=&oldPrimaryDisplayPropertyType=&newHome=&auction=false'
res = requests.get(url)
soup = BeautifulSoup(res.content, 'html.parser')
random_props = np.unique(['https://www.rightmove.co.uk'+i['href'] for i in soup.find_all(class_='propertyCard-link')])

m = leafmap.Map(center=(36.3, 0), zoom=2)
m.add_basemap("HYBRID")
        
@st.cache
def get_iod_doogal(postcode):
    postcode = postcode.lower().strip()
    url = f"https://www.doogal.co.uk/ShowMap.php?postcode={postcode}"
    r = requests.get(url)

    soup = BeautifulSoup(r.content, 'html.parser')

    dep_line = soup.find_all(text=re.compile('/ 32,844'))
    if len(dep_line) == 1:
        deprivation = int(dep_line[0].split('/')[0].replace(',',''))
        return deprivation
    else:
        return None
    
#@st.cache
def get_lon_lat(rightm_soup):
    data = json.loads(rightm_soup.find(text=re.compile('latitude')).string[25:])['propertyData']['location']

    longitude = data['longitude']
    latitude = data['latitude']
    
    return longitude, latitude

@st.cache
def lon_lat_to_postcode(lon, lat):
    if lat is not None and lon is not None:
        url = f' http://api.postcodes.io/postcodes?lon={lon}&lat={lat}'
        res = requests.get(url)
        if res.status_code == 200:
            result = json.loads(res.content)['result']
            if result is not None:
                return result[0]['postcode']
            else:
                return None
        else:
            return None
    else:
        return None

#@st.cache
def get_address(rightm_soup):
    pat = r"\b([A-Za-z][A-Za-z]?[0-9][0-9]?[A-Za-z]?)\b"
    address = rightm_soup.find(re.compile(pat)).string
    return address
    
@st.cache
def get_outcode(address):
    outcode_pat = '^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([AZa-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z]))))[0-9][A-Za-z]{2})$'
    if len(address.split(',')[-1].strip())==3:
        return(re.match(outcode_pat, (address+'2QZ').split(',')[-1].strip()).group(0)[:3])
    else:
        return None
        
@st.cache
def get_layers(url):
    options = leafmap.get_wms_layers(url)
    return options


def app():
    streamlit_analytics.start_tracking()
    st.title("Rightmove house finder for Mum and Dad")
    st.markdown(
        """
    This app displays the location of a property listed on Rightmove, alongside information about noise pollution and flooding extent (modify layers in top-right of map). It also looks up information relevant to the property and the local area (second column).
    """
    )

    row1_col1, row1_col2 = st.columns([3, 1.3])
    width = 800
    height = 600
    layers = None
    
    lat = None
    lon = None
   
    with row1_col2:
    
        initial = "https://www.rightmove.co.uk/properties/118322783#/"
    
        container = st.container()
        container.write('')
    
        #empty = st.empty()
        st.write('or')
        aa = st.button('Choose a random property in the Stroud area')
        if aa:
            initial = np.random.choice(random_props)
        
        rightm_url = container.text_input(
        "Enter Rightmove URL:", value=initial
        )
       
        r = requests.get(rightm_url)
        if 'we’re sorry, we couldn’t find the property'.lower() in r.text.lower():
            st.error('Invalid Rightmove URL')
        else:
            
            
            rightm_soup = BeautifulSoup(r.content, 'html.parser')
            lon, lat = get_lon_lat(rightm_soup)
        
            info_header = st.container()
                              
            if lat is not None and lon is not None:
                data = pd.DataFrame({'longitude': [lon], 'latitude': [lat], 'address': 'house1'})
                
                m = leafmap.Map(center=(36.3, 0), zoom=2)
                m.add_basemap("HYBRID")
                m.add_points_from_xy(data, x='longitude', y='latitude', popup=['address'], layer_name='House marker')
       
                centre = shapely.geometry.Point(lon, lat).buffer(.05)
                m.zoom_to_bounds(centre.bounds)
          
                with st.container():
                    st.info(rightm_url)
                    st.caption(f'Acquired coordinates ({lat}, {lon})')
                                   
                container2 = st.container()
                container2.write('')
                
                postcode = lon_lat_to_postcode(lon, lat)
                if postcode is not None:
                    st.write(f'Full postcode from coordinates: {postcode}')
            
                address = get_address(rightm_soup)
                if address is not None:
                    info_header.subheader(f'{address}')
            
                    if postcode is None:
                        outcode = get_outcode(address)
                        if outcode is not None:
                            container2.write(f'Outcode: \n{outcode}')
                else:
                    info_header.subheader('Info')
                            
                if b'garage' in r.content.lower():
                    st.write('A garage is mentioned in this property listing.')
                
                if postcode is not None:
                        iod_score = get_iod_doogal(postcode)
                        if iod_score is not None:
                            #st.write(iod_score)
                            st.metric(label="Index of Multiple Deprivation (2019)", value=f"{iod_score:,} / 32,844")
                            
                            if iod_score <= 18000:
                                st.caption('The Index of Multiple Deprivation is below 18,000. Cars lay torched in the street. England flags are draped across a sea of white vans. Brutes scoff pies in the street. Distant screaming can be heard.')
                            else:
                                st.caption('The Index of Multiple Deprivation is above 18,000. Please note that this is a loose proxy for access to local amenities and should be considered alongside other factors.')

                            st.progress(iod_score/32844.)
                            
                desc = [i.string for i in rightm_soup.find_all('script')]
                for d in desc:
                    if d is not None:
                        if 'window.PAGE_MODEL' in d.string:
                            desc = json.loads( ''.join(d.split('= ')[1:]) )
                            desc = desc['propertyData']['text']['description']
                            with st.expander('Description'):
                                st.markdown(desc, unsafe_allow_html=True)
                            
                fp_img = rightm_soup.find('img', {'alt': 'Floorplan'})
                if fp_img is not None:
                    with st.expander('Floorplan', expanded=False):
                        st.image(fp_img.get('src'))
                    
                with st.expander('Property pictures', expanded=False):
                     pic_urls = [i.get('content') for i in rightm_soup.find_all('meta', property='og:image')]
                     st.image(pic_urls)
                    
    with row1_col1:
   
        road_noise = 'https://environment.data.gov.uk/spatialdata/road-noise-lden-england-round-3/wms'
        m.add_wms_layer(url=road_noise, layers='Road_Noise_Lden_England_Round_3', name='Road_Noise_Lden_England_Round_3', format='image/png', shown=True, transparent=True)

        rail_noise = 'https://environment.data.gov.uk/spatialdata/rail-noise-lden-england-round-3/wms'
        m.add_wms_layer(url=rail_noise, layers='Rail_Noise_Lden_England_Round_3', name='Rail_Noise_Lden_England_Round_3', format='image/png', shown=True, transparent=True)

        flood_zone2 = 'https://environment.data.gov.uk/spatialdata/flood-map-for-planning-rivers-and-sea-flood-zone-2/wms'
        m.add_wms_layer(url=flood_zone2, layers='Flood_Map_for_Planning_Rivers_and_Sea_Flood_Zone_2', name='Flood_Map_for_Planning_Rivers_and_Sea_Flood_Zone_2', format='image/png', shown=True, transparent=True)

        if lat is not None and lon is not None:
           data = pd.DataFrame({'longitude': [lon], 'latitude': [lat], 'address': 'house1'})
           m.add_points_from_xy(data, x='longitude', y='latitude', popup=['address'], layer_name='House marker')
       
           centre = shapely.geometry.Point(lon, lat).buffer(.005)
           m.zoom_to_bounds(centre.bounds)

        m.to_streamlit(width, height)
        
    streamlit_analytics.stop_tracking()
        
            
if __name__ == '__main__':
    app()
