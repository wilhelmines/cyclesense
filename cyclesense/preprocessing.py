# Add a column to the pandas df that automatically adds an id for each trip based on given params

def trip_creation(df, Datum='Datum', Zeit='Zeit', Pause=900):
    def trip_creation_helper(df, Datum, Zeit, Pause):
        # Convert 'Datum' and 'Zeit' to datetime
        df['Datetime'] = pd.to_datetime(df[Datum] + ' ' + df[Zeit])

        # Sort by 'Datetime' and 'ID'
        df = df.sort_values(['ID', 'Datetime'])

        # Calculate the difference in seconds between each 'Datetime' and the previous one
        df['TimeDiff'] = df.groupby('ID')['Datetime'].diff().dt.total_seconds()

        # Identify each unique trip
        df['Trip'] = (df['ID'] != df['ID'].shift()) | (df[Datum] != df[Datum].shift())

        # Identify each unique trip
        df['Trip'] = (df['ID'] != df['ID'].shift()) | (df['TimeDiff'] > Pause)

        # Add an ID for each trip
        df = df.assign(Trip_ID = df['Trip'].cumsum())

        return df['Trip_ID']

    df['Trip_ID'] = trip_creation_helper(df, Datum, Zeit, Pause)
    return


# Calculate distance between consecutive points within each trip
def calculate_trip_duration(df):
    trip_duration = df.groupby('Trip_ID')['Datetime'].apply(lambda x: x.max() - x.min()).reset_index()
    trip_duration['TripDuration'] = trip_duration['Datetime'].dt.total_seconds()
    return trip_duration[['Trip_ID', 'TripDuration']]

# Calculate the sum of dat points for each trip
def calculate_data_points(df):
    data_points = df.groupby('Trip_ID').size().reset_index(name='DataPoints')
    return data_points

def calculate_trip_distances(df):
    # Create a copy of the DataFrame
    df_copy = df.copy()

    # Create new columns for the previous latitudes and longitudes
    df_copy['Prev_Latitude'] = df_copy.groupby('Trip_ID')['Breitengrad'].shift()
    df_copy['Prev_Longitude'] = df_copy.groupby('Trip_ID')['Laengengrad'].shift()

    # Drop the first row of each trip (since it doesn't have a previous point)
    df_copy.dropna(subset=['Prev_Latitude', 'Prev_Longitude'], inplace=True)

    # Calculate distance between consecutive points
    df_copy['Distance'] = df_copy.apply(lambda row: geodesic((row['Prev_Latitude'], row['Prev_Longitude']), (row['Breitengrad'], row['Laengengrad'])).km, axis=1)

    # Calculate total distance for each trip
    trip_distances = df_copy.groupby('Trip_ID')['Distance'].sum().reset_index()

    return trip_distances

#Drop trips with less then 'cutoff' datapoints
def drop_short_trips(df, cutoff=5):
    data_points= calculate_data_points(df)
    trips_drop = data_points[data_points.DataPoints <= cutoff]
    df = df[~df['Trip_ID'].isin(trips_drop['Trip_ID'])]
    return df

def create_metrics_table(df):
    trips_temp = pd.merge(calculate_trip_duration(df), calculate_data_points(df), on='Trip_ID')
    trips = pd.merge(trips_temp, calculate_trip_distances(df), on='Trip_ID')
    return trips

def calculate_trip_mean_speed(df, Trip_ID='Trip_ID', Datetime='Datetime', Breitengrad='Breitengrad', Laengengrad='Laengengrad'):
    # Assuming your DataFrame is named df, the timestamp column is named 'timestamp'
    # and is in seconds, and the coordinates are in columns 'latitude' and 'longitude'
    df = df.sort_values([Trip_ID, Datetime])

    # Calculate the distance to the next point in each trip in kilometers
    df['distance'] = np.sqrt((df[Breitengrad].diff().pow(2) + df[Laengengrad].diff().pow(2))) * 111

    # Calculate the time difference to the next timestamp in each trip in hours
    df['time_diff'] = df[Datetime].diff().dt.total_seconds().abs() / 3600
    # Calculate the speed in km/h
    df['speed'] = df['distance'] / df['time_diff']

    # Replace infinite values with NaN
    df['speed'] = df['speed'].replace([np.inf, -np.inf], np.nan)

    return df