from flask import Flask, jsonify, request
from flask_cors import CORS


import numpy as np
import pandas as pd


from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import json
import firebase_admin
from firebase_admin import credentials, db
from sklearn.neighbors import KNeighborsRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline 
from geopy.distance import geodesic
import os
from pathlib import Path

# Get the current directory of the script
current_directory = Path(__file__).resolve().parent

# Adjust the filename and construct the new path using .\ explicitly
file_name = "patchnet-b35d6-firebase-adminsdk-12855-b014335dbf.json"
file_path = current_directory / file_name

# Use the constructed file path
cred = credentials.Certificate(str(file_path))





# cred = credentials.Certificate(".\patchnet-b35d6-firebase-adminsdk-12855-b014335dbf.json")

# Check if the app is already initialized
try:
    firebase_admin.get_app()
except ValueError:
    # Initialize the app only if it's not already initialized
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://patchnet-b35d6-default-rtdb.firebaseio.com/'
    })

user_location_ref = db.reference('user_location')

user_location_data = user_location_ref.get()

# Create a list of dictionaries for each user
user_data = []

# Iterate through the users and create dictionaries for each user
for user_info in user_location_data.values():
    user_dict = {
        'networkSpeed': user_info['networkSpeed'],
        'SimName': user_info['SimName'],
        'latitude': user_info['latitude'],
        'longitude': user_info['longitude']
    }
    user_data.append(user_dict)

# Print the list of dictionaries
# for user_dict in user_data:
#     print(user_dict)
# print(user_data)
df = pd.DataFrame(user_data)

app = Flask(__name__)
CORS(app)





@app.route('/predict', methods=['GET'])
def predict():
    # sim_name = request.args.get('SimName')
    filtered_user_data = [data for data in user_data if data['SimName'] == 'airtel']
    coordinates = np.array([[data['latitude'], data['longitude'], data['networkSpeed']] for data in filtered_user_data])

# Standardize the data
    coordinates = StandardScaler().fit_transform(coordinates)

# Apply DBSCAN algorithm with three parameters
    eps_value = 0.9  # Adjust the epsilon (eps) value based on your data
    min_samples_value = 3  # Adjust the min_samples value based on your data
    dbscan = DBSCAN(eps=eps_value, min_samples=min_samples_value)
    clusters = dbscan.fit_predict(coordinates)

    # Extracting coordinates and network speed from user data for a specific provider (e.g., 'Jio')

    

    # Add the cluster information to the Jio user data
    for i, cluster in enumerate(clusters):
        filtered_user_data[i]['Cluster'] = cluster

    # Store clustered data in a dictionary
    clustered_data = {}
    unique_clusters = np.unique(clusters)
    for cluster_label in unique_clusters:
        cluster_points = [
            {k: int(v) if isinstance(v, np.int64) else v for k, v in data.items()}
            for data in filtered_user_data if data['Cluster'] == cluster_label
        ]
        clustered_data[f'Cluster {cluster_label}'] = cluster_points

    # Convert clustered data to JSON format using custom encoder
    json_clustered_data = json.dumps(clustered_data, default=lambda x: int(x) if isinstance(x, np.int64) else x)
    data = json.loads(json_clustered_data)

# Calculate average network speed for each cluster
   

# Calculate average network speed for each cluster
    average_speeds = {}
    for cluster, users in data.items():
    # Extract network speeds for users in the cluster
        speeds = [user['networkSpeed'] for user in users]
    
    # Calculate average speed for the cluster
        average_speed = sum(speeds) / len(speeds) if len(speeds) > 0 else 0
    
    # Store the average speed for the cluster
        average_speeds[cluster] = average_speed

# Display average speeds for each cluster
    for cluster, users in data.items():
        for user in users:
          user['AverageNetworkSpeed'] = average_speeds[cluster]
          

# Convert back to JSON string
    
    
    updated_json_data = json.dumps(data, indent=2)


    return updated_json_data


  # You may need to install geopy using: pip install geopy

# Assuming 'df' is your DataFrame containing the data

# Convert 'simName' column to categorical and encode it
@app.route('/add', methods=['GET'])
def add():
  

# Assuming 'df' is your DataFrame containing user data

# Convert 'SimName' to categorical codes
    latitude = float(request.args.get('latitude'))
    longitude = float(request.args.get('longitude'))
    simName = request.args.get('simName')
    networkSpeed = float(request.args.get('networkSpeed'))
    df['simName'] = pd.Categorical(df['SimName'])
    df['simName'] = df['simName'].cat.codes
    # print(df['simName'])

    # Define features and target
    X = df[['latitude', 'longitude', 'simName', 'networkSpeed']]
    y = df['networkSpeed']

    # Define transformers for numerical and categorical features
    numerical_features = ['latitude', 'longitude', 'networkSpeed', 'simName']
    categorical_features = []  # Add categorical features if any

    numerical_transformer = StandardScaler()
    categorical_transformer = OneHotEncoder()

    # Create preprocessor using ColumnTransformer
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numerical_transformer, numerical_features),
            ('cat', categorical_transformer, categorical_features)
        ])

    # Create KNN regressor model
    knn_model = KNeighborsRegressor(n_neighbors=20)

    # Create a Pipeline with preprocessor and KNN model
    model = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', knn_model)
    ])

    # Fit the model
    model.fit(X, y)

    # New user data
    

    # Create new_user_data from the received parameters
    new_user_data = pd.DataFrame({
        'latitude': [latitude],
        'longitude': [longitude],
        'simName': [simName],
        'networkSpeed': [networkSpeed]
    })
    new_user_data['simName'] = pd.Categorical(new_user_data['simName'])
    new_user_data['simName'] = new_user_data['simName'].cat.codes
    print(new_user_data['simName'])

    # Transform new user data using preprocessor
    new_user_data_scaled = preprocessor.transform(new_user_data)

    # Find nearest neighbors for new user data
    distances, indices = knn_model.kneighbors(new_user_data_scaled, n_neighbors=15)

    # Get new user coordinates
    new_user_coords = (new_user_data['latitude'].values[0], new_user_data['longitude'].values[0])

    # Get the top 5 nearest users based on distance and network speed
    top_5_users = df.iloc[indices[0]]
    top_5_users['Distance'] = top_5_users.apply(
        lambda row: geodesic(new_user_coords, (row['latitude'], row['longitude'])).kilometers, axis=1)
    filtered_top_5 = top_5_users[top_5_users['networkSpeed'] > new_user_data['networkSpeed'].values[0]]
    sorted_filtered_top_5 = filtered_top_5.sort_values(by='Distance', ascending=True)
    final_top_5 = sorted_filtered_top_5.head(5)

    # Print the top 5 recommended users
    print(final_top_5[['latitude', 'longitude', 'networkSpeed', 'simName', 'Distance']])
    top_5_json = final_top_5[['latitude', 'longitude', 'networkSpeed', 'simName', 'Distance']].to_json(orient='records')
    user_data = {}
    data = json.loads(top_5_json)

# Create a dictionary with string keys ('user1', 'user2', etc.) and respective values

    user_data = {f"user{i + 1}": obj for i, obj in enumerate(data)}

    # Convert the user_data dictionary to a JSON string
    user_data_json = json.dumps(user_data, indent=2)
    print(user_data_json)
    

    return user_data_json


    # Assuming 'user_data' is the list of dictionaries containing user information

    # Convert 'SimName' column to categorical and encode it
    
    

if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0')


