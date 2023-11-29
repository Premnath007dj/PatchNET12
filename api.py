from flask import Flask, jsonify, request
from flask_cors import CORS


import numpy as np

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import json
import firebase_admin
from firebase_admin import credentials, db

cred = credentials.Certificate(r"C:\Users\premnath\Downloads\ptt\patchnet-b35d6-firebase-adminsdk-12855-b014335dbf.json")

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
for user_dict in user_data:
    print(user_dict)
print(user_data)

app = Flask(__name__)
CORS(app)





@app.route('/predict', methods=['GET'])
def predict():
    airtel_user_data = [data for data in user_data if data['SimName'] == 'airtel']
    coordinates = np.array([[data['latitude'], data['longitude'], data['networkSpeed']] for data in airtel_user_data])

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
        airtel_user_data[i]['Cluster'] = cluster

    # Store clustered data in a dictionary
    clustered_data = {}
    unique_clusters = np.unique(clusters)
    for cluster_label in unique_clusters:
        cluster_points = [
            {k: int(v) if isinstance(v, np.int64) else v for k, v in data.items()}
            for data in airtel_user_data if data['Cluster'] == cluster_label
        ]
        clustered_data[f'Cluster {cluster_label}'] = cluster_points

    # Convert clustered data to JSON format using custom encoder
    json_clustered_data = json.dumps(clustered_data, default=lambda x: int(x) if isinstance(x, np.int64) else x)

    return json_clustered_data
@app.route('/add', methods=['GET'])
def add():
    num1 = request.args.get('num1', 0, type=float)
    num2 = request.args.get('num2', 0, type=float)
    
    result = num1 + num2
    return jsonify({"result": result})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

