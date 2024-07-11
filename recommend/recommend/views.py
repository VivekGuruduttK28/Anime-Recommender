import csv
import json
import numpy as np
import pandas as pd
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import os
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def recommender(request):
    # Assuming the request contains JSON data with the anime_name field
    data = json.loads(request.body.decode('utf-8'))
    anime_name = data.get('anime_name').lower() # No need to convert to lowercase here
    print(anime_name)
    # Attempt to fetch data from cache
    cached_data = cache.get('cached_csv_data')
    animemat = cache.get('animemat')
    weighted_data = cache.get('weighted_data')

    if cached_data is None:
        # Data not found in cache, load from CSV file
        csv=os.path.join(settings.BASE_DIR,'anime_updated.csv')
        anime=pd.read_csv(csv)
        csv=os.path.join(settings.BASE_DIR,'rating_updated.csv')
        rating=pd.read_csv(csv)
        data=pd.merge(anime,rating,on='anime_id',suffixes=[None,'_user'])
        data=data.rename(columns={'rating_user':'user_rating'})
        data['user_rating'].replace(to_replace=-1,value=np.nan,inplace=True)
        data=data.dropna(axis=0)
        no_of_reviews=data.groupby('anime_id').size().reset_index()
        no_of_reviews.columns=['anime_id','review_count']
        data=data.merge(no_of_reviews,on='anime_id')
        data.name=data.name.str.lower()

        animemat = data.pivot_table(index='user_id', columns='name', values='user_rating')
        weighted_data = data.groupby('anime_id')[['name', 'rating', 'review_count', 'members']].max().reset_index()
        
        # Store data in cache
        cache.set('cached_csv_data', data)
        cache.set('animemat',animemat)
        cache.set('weighted_data',weighted_data)
    else:
        data = cached_data

    

    try:
        user_ratings=animemat[anime_name]
        similar_to_x=animemat.corrwith(user_ratings)
        corr_x=pd.DataFrame(similar_to_x,columns=['Correlation']).reset_index()
        corr_x.dropna(inplace=True)
        corr_x=corr_x.merge(weighted_data[['review_count','name']],on='name')
        rec=corr_x[corr_x['review_count']>100].sort_values('Correlation',ascending=False).head(5)
        recommended_animes = list(rec['name'])

        return JsonResponse({'data': recommended_animes})

    except KeyError as e:
        print("Give a valid anime name")
        return JsonResponse({'error': 'Invalid anime name'}, status=400)
