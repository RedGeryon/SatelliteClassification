import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import geopandas as gpd
import seaborn as sns
import fiona
import fiona.crs
import matplotlib.pyplot as plt
from PIL import Image

def load_shapefile(path, zipcodes=[]):
    '''Given filepath to ZTCA (zipcode) shapefile of the US, only load
    the zipcodes of interest. Also simplify column types for less memory
    footprint.
    
    Args:
        path (str): String path to shapefile
        zipcodes (list): List of 5 digit string zipcodes of interest
        
    Return:
        GeoPandas obj: Returns a GeoPandas dataframe
    '''
    
    data = gpd.read_file(path)
    if zipcodes:
        data = data[data['ZCTA5CE10'].isin(zipcodes)]
    return data

def subset_aoi(aoi, shape, save_fp, intersect=True):
    '''To take up less memory in RAM, we will subset our shapefiles to an
    area of interest and output it to file.
    
    Args:
        aoi (GeoPandas obj): Object with geometry containing only AOI
        shape (GeoPandas obj): Shape object to be trimmed to intersection
        save_fp (str): Filepath for new shapefile (should end in .shp)
    
    Return:
        bool: True if new shapefile has been sucessfully dumped to file, else False.
    '''
    
    try:
        # Intersecting merges geometry data, sometimes we that, other times we just
        # want the areas of overlap, but not the merged geometries.
        if intersect:
            print('Intersecting {save_fp} with aoi...')
            new = gpd.overlay(aoi, shape, how='intersection')
            print('Dumping to new shapefile to file...')
            new.to_file(save_fp)
            del new
            return True
        else:
            # Keep track of overlap here, return stuff in 2nd shape that
            # overlapped with first.
            osm_id = []
            temp_shape = gpd.tools.sjoin(aoi, shape, how='inner', op='intersects')
            osm_id = temp_shape['osm_id'].values
            shape[shape['osm_id'].isin(osm_id)].to_file(save_fp)
            return True
    except Exception as e:
        try:
            print(e)
            print('Trying a join method to compare polygon and 1D/dot geometries.')
            osm_id = []
            temp_shape = gpd.tools.sjoin(aoi, shape, how='inner', op='intersects')
            osm_id = temp_shape['osm_id'].values
            shape[shape['osm_id'].isin(osm_id)].to_file(save_fp)
            return True
        except Exception as e:
            print(e)
            print('Error dumping to file, giving up!')
            return False

def plot_shapefile(shapefiles, graph_settings=False):
    '''This is a helper function to plot any number of geopandas object

    Args:
        shapefiles (list): list of geopandas objects to be plotted
        graph_settings (dict): list of parameters that user can manually set
            'save' - savename for file
            'format' - save format
            'edgecolor' - edgecolor for geopandas geometries
            'color' - fill colors for geopandas geometries

    Return: None
    '''
    default = {'save': '',
               'format': 'png',
               'edgecolor': iter(sns.color_palette("Paired")),
               'color': iter(sns.color_palette("Paired"))}
    
    if graph_settings:
        for k,v in graph_settings.items():
            default[k] = v
    
    f, ax = plt.subplots(figsize=(40,40))

    
    i= 0
    
    for s in shapefiles:
        # Change plot color options if given in graph_settings
        if type(default['edgecolor']) != str:
            edge = next(default['edgecolor'])
        else:
            edge = default['edgecolor']
        if type(default['color']) != str:
            col = next(default['color'])
        else:
            col = default['color']

        s.plot(ax=ax, color=col, edgecolor=edge)
        i+=1
    ax.grid(False)
    sns.set_style("whitegrid")
    if default['save']:
        f.savefig(default['save'], format=default['format'])

def peel_geodatabase():
    '''ACS 2016 survey data is an ESRI geodatabase. It is unwieldy and has multiple
    layers, one of which is a geospatial blockgroup reference (includes geometry to
    segregate blockgroups). To take the data we need, this module peels the layers
    (tabular data with georeference) and outputs to json, or geojson for our 
    blockgroup geometry layer.
    '''
    datasrc_path='./data/2016blockgroupca.gdb'

    layers = fiona.listlayers(datasrc_path)
    for layer_name in layers: 
        features = []
        if layer_name == 'ACS_2016_5YR_BG_06_CALIFORNIA':
            kwargs = {'path': datasrc_path,
                      'layer' : layer_name, 
                      'driver': 'OpenFileGDB'}
        else:
            kwargs = {'path': datasrc_path,
                      'layer' : layer_name}
        with fiona.open(**kwargs) as collection:
            # We need to handle geopandas data differently than regular tabular data
            # because of diff dict structures and one is a nested OrderedDict type
            if layer_name == 'ACS_2016_5YR_BG_06_CALIFORNIA':
                print(f'Dumping {layer_name} to shapefile')
                with fiona.open('./data/ACS2016/' + layer_name + '.shp', 'w',
                        driver='ESRI Shapefile',
                        crs = collection.crs,
                        schema=collection.schema) as sink:
                    for feature in collection:
                        sink.write(feature)
            else:
                print(f'Dumping {layer_name} to csv')
                for feature in collection:
                    features.append(feature['properties'])
                df = pd.DataFrame(features)
                with open('./data/ACS2016/' + layer_name + '.csv', 'w') as f:
                    f.write(df.to_csv())

def show_image(fp, save_path='', infrared=False):
    '''View satellite image with 4 bands (technically ok with
    any number of bands beyond 3).

    Args:
    fp (str): Path to sallite image file
    save_path (str): Path to save file if user wants to save
    infrared (bool): Set to True if user wants to view infrared band
    
    Return: None - will optionally output save file
    '''
    im = Image.open(fp)
    im = np.array(im)
    
    # If infrared, exclude first band, include last,
    # else only use first 3 bands (RGB)
    if infrared:
        im = im[:,:,1:]
    else:
        im = im[:,:,:3]

    f, ax = plt.subplots(figsize=(40,40))
    plt.imshow(im[:,:,:])
    if save_path:
        f.savefig(save_path)