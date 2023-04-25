#!/usr/bin/env python3
# -*- coding: utf-8 -*-


"""
Analyse the clustering result of pixplot.

Prozess:
- Run pixplot on a set of images
- Analyse pixplot results visually and detect clusters of interest
- Optional: Create a user hotspot using pixplot
- Run this python script

This script does:
- identify the images contained within the clusters of interest (dataframe image_selected)
- search for selected images representing the first page of a Transkribus document (will be printed to console)
- identify selected images representing the last page of a Transkribus document (dataframe image_selected_last). The images will be copied in a separate folder.
- identify images representing pages of a Transkribus document that are between selected images (dataframe image_between_selected). The images will be copied in a separate folder.
- choose randomly 1000 selected images and copy them into a separate folder "selected_sample" to analyse what proportion of selected images might be wrong selected.
- choose randomliy 1000 images and copy them into a separate folder "random_sample". If for those images all truly to be selected images are listed in to_be_selected.txt,
  a comparison will be done between the selected/not selected images and the true/false Brandlagerbücher.
"""


import json
import pandas as pd
import re
import glob
import shutil
import os
import random
random.seed(1)


def get_selected_images(hotspot, imagelist, cluster_of_interest):
    '''Returns a dataframe of all images of selected clusters.'''

    image_index = []
    for cluster in cluster_of_interest:
        image_index += hotspot[hotspot['label'] == cluster]['images'].values[0]

    return imagelist.iloc[image_index]


def get_page_nr(filename):
    '''Return the page number of a Transkribus document.'''
    
    try:
        return int(re.search(r'[0-9]{3}.jpg', filename).group()[:3])
    except:
       return None


def get_doc_title(filename):
    '''Return the document title (identifier) of a Transkribus document.'''
    
    try:
        return re.search(r'HGB_[0-9]{1}_[0-9]{3}_[0-9]{3}', filename).group()
    except:
       return None


def copy_image(filename, source_directory, destination_directory):
    '''Copy a specific file from a given source directory to a given destination directory.''' 

    filepath = glob.glob(f'{source_directory}/{filename}')[0]
    
    # Create destination directory if not exist
    if not os.path.exists(destination_directory):
        os.mkdir(destination_directory)

    # Copy image
    shutil.copy(filepath, f'{destination_directory}/{filename}')


def get_filename(doc_title, page_nr):
    '''Given the Transkribus document title (identifier) and the page number as integer, returns the filename of the image.'''

    try:
        return f'{doc_title}_{page_nr:03}.jpg'
    except:
       return None


def validate_result(filename, image_selected, to_be_selected):
    '''Validates if image in random sample set is correct selected or not.'''
    
    try:
        if filename in image_selected['filename'].values:
            if filename in to_be_selected['filename'].values:
                return 'correct selected'
            else:
                return 'wrong selected'
        else:
            if filename in to_be_selected['filename'].values:
                return 'wrong not selected'
            else:
                return 'correct not selected'
    except:
       return None


if __name__ == "__main__":

    ##
    # Set parameters
    ##

    # UUID of pixplot run
    uuid = '26a16624-ce6a-11ed-aadf-0050b6fb31c5' # HGB (all images)

    # cluster labels containing the images of interest (Brandlagerbücher)
    cluster_of_interest = ['Cluster 8', 'Cluster 9'] # HGB (all images)

    # Path to the pixplot output
    path_output = 'C:/Users/jonas/output/data'

    # Optional: set directory to a user hotspot
    path_user_hotspot = 'C:/Users/jonas/output/data/hotspots/user_hotspots.json' # HGB (all images), main clusters of Cluster 8 and Cluster 9
    user_cluster_of_interest = ['Brandlagerbuecher']


    ##
    # Identify selected images
    ##

    # Read pixplot clusters
    hotspot = pd.read_json(f'{path_output}/hotspots/hotspot-{uuid}.json')

    # Read image filenames
    with open(f'{path_output}/imagelists/imagelist-{uuid}.json') as jsonFile:
        imagelist = json.load(jsonFile)['images']
    imagelist = pd.DataFrame(imagelist, columns=['filename'])

    # Get selected images
    image_selected = get_selected_images(hotspot, imagelist, cluster_of_interest)

    # Extract page number from filename
    image_selected['doc_title'] = image_selected.apply(lambda row: get_doc_title(row['filename']), axis=1)
    image_selected['page_nr'] = image_selected.apply(lambda row: get_page_nr(row['filename']), axis=1)

    # Calculate the number of selected images
    print(f'{image_selected.shape[0]} images selected out of {imagelist.shape[0]} ({round(image_selected.shape[0] / imagelist.shape[0] * 100)}%).')


    ##
    # Detect selected images on first document page
    ##

    # Detect selected images representing a first document page
    print(f'{image_selected[image_selected["page_nr"] == 1].shape[0]} images are selected corresponding to the first page of a document.')


    ##
    # Detect selected images on last document page
    ##

    # Within imagelist, extract doc_title and page_nr
    imagelist['doc_title'] = imagelist.apply(lambda row: get_doc_title(row['filename']), axis=1)
    imagelist['page_nr'] = imagelist.apply(lambda row: get_page_nr(row['filename']), axis=1)

    # Get the number of pages for each Transkribus document
    n_pages = pd.DataFrame({'nr_of_pages': imagelist.groupby('doc_title')['page_nr'].max()})

    # Join the number of pages to the selected images
    image_selected = image_selected.join(n_pages, on='doc_title')

    # Get the selected images corresponding to the last page of a Transkribus document
    image_selected_last = image_selected[image_selected['page_nr'] == image_selected['nr_of_pages']]

    # Copy images of selected pages to folder selected_last_page
    source_directory = f'{path_output}/originals'
    destination_directory = f'{path_output}/{uuid}_selected_last_page'
    image_selected_last.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)


    ##
    # Detect images lying between selected images
    ##

    # Determine pages that are between selected pages
    image_between_selected = pd.DataFrame(columns=['doc_title', 'page_nr'])

    # Iterate over Transkribus documents
    selected_grouped = image_selected.groupby('doc_title')
    for name, group in selected_grouped:     
        group.sort_values('page_nr', inplace=True)
    
        # Iterate over pages
        page_nr_last = None
        for index, row in group.iterrows():
            page_nr_current = row['page_nr']
        
            # First iteration
            if not page_nr_last:
                page_nr_last = page_nr_current

            # Current page is selected too
            elif page_nr_current == page_nr_last + 1:
                page_nr_last = page_nr_current
        
            # Page between selected pages found
            else:
                page_nr = page_nr_last + 1
                while page_nr != page_nr_current:
                    new_entry = pd.DataFrame({'doc_title': [name], 'page_nr': [page_nr]}) 
                    image_between_selected = pd.concat([image_between_selected, new_entry], ignore_index=True)
                    page_nr += 1
                page_nr_last = page_nr_current

    # Get filenames of pages lying between selected pages
    image_between_selected['filename'] = image_between_selected.apply(lambda row: get_filename(row['doc_title'], row['page_nr']), axis=1)

    # Copy images of pages between selected pages to folder between_selected
    destination_directory = f'{path_output}/{uuid}_between_selected'
    if image_between_selected.shape[0] > 1000:
        # Select randomly 1000 pages
        image_between_selected_sample = image_between_selected.iloc[random.sample(range(image_between_selected.shape[0]), 1000)]
        image_between_selected_sample.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)
    else:
        image_between_selected.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)


    ##
    # Select randomly selected images
    ##

    # Select randomly 1000 selected images
    image_selected_sample = image_selected.iloc[random.sample(range(image_selected.shape[0]), 1000)]

    # Copy images of randomly selected images to folder selected_sample
    destination_directory = f'{path_output}/{uuid}_selected_sample'
    image_selected_sample.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)


    ##
    # Select randomly images
    ##

    # Select randomly 1000 images
    image_sample = imagelist.iloc[random.sample(range(imagelist.shape[0]), 1000)]

    # Copy images of random images to folder random_sample
    destination_directory = f'{path_output}/{uuid}_random_sample'
    image_sample.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)

    # Validate how many image samples are correct and wrong detected.
    try:
        to_be_selected = pd.read_table(f'{destination_directory}/to_be_selected.txt')
        image_sample['validation'] = image_sample.apply(lambda row: validate_result(row['filename'], image_selected, to_be_selected), axis=1)
        print(f"Validation result: \n{pd.crosstab(index='summary', columns=image_sample['validation'])}")
    except:
        print(f'Please analyse the true images to select in {destination_directory} and create to_be_selected.txt.')


    ##
    # Write results
    ##

    # Save imagelist and selected images
    imagelist.to_csv(f'{path_output}/{uuid}_imagelist.csv', index=False)
    image_selected.to_csv(f'{path_output}/{uuid}_image_selected.csv', index=False)
    image_sample.to_csv(f'{path_output}/{uuid}_image_sample.csv', index=False)


    ##
    # Analyze user clusters
    ##

    if path_user_hotspot:
        
        # Read pixplot clusters
        user_hotspot = pd.read_json(path_user_hotspot)

        # Get selected images
        user_image_selected = get_selected_images(user_hotspot, imagelist, user_cluster_of_interest)

        # Select randomly 1000 selected images
        user_image_selected_sample = user_image_selected.iloc[random.sample(range(user_image_selected.shape[0]), 1000)]

        # Copy images of randomly selected images to folder selected_sample
        destination_directory = f'{path_output}/{uuid}_selected_sample_user'
        user_image_selected_sample.apply(lambda row: copy_image(row['filename'], source_directory, destination_directory), axis=1)

        # Save selected images
        user_image_selected.to_csv(f'{path_output}/{uuid}_image_selected_user.csv', index=False)
        