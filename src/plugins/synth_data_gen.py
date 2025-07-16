import random
from datetime import datetime, timedelta
from collections import Counter

def supported_cities_search() -> dict:
    """
    Renders a list of supported cities and continent eacg belongs to.
    Supported cities include major cities from North America, South America, Europe, Asia, and Africa.
    """
    city_continent_map = {
        "New York": "North America", "Toronto": "North America", "Los Angeles": "North America", "Mexico City": "North America",
        "São Paulo": "South America", "Buenos Aires": "South America", "Lima": "South America", "Bogotá": "South America",
        "London": "Europe", "Paris": "Europe", "Berlin": "Europe", "Rome": "Europe",
        "Tokyo": "Asia", "Beijing": "Asia", "Mumbai": "Asia", "Bangkok": "Asia",
        "Cairo": "Africa", "Lagos": "Africa", "Nairobi": "Africa", "Cape Town": "Africa"
    }
    return city_continent_map

def weather_by_city_search(city_name:str) -> dict:
    """
    Renders a 7-day weather forecast for a supported city. Your response should include the current weather, a weekly forecast, and summary statistics.

    Args:
        city_name (str): The name of the city to get the weather forecast for. 
            Supported cities include major cities from North America, South America, Europe, Asia, and Africa.

    Returns:
        dict: A dictionary containing:
            - city (str): The city name.
            - continent (str): The continent of the city.
            - current_temperature_c (float): The simulated current temperature in Celsius.
            - current_humidity_percent (int): The simulated current humidity percentage.
            - current_condition (str): The simulated current weather condition.
            - timestamp (str): The ISO formatted timestamp of the forecast.
            - weekly_forecast (list): A list of daily weather data for the next 7 days.
            - weekly_summary (dict): Summary statistics for the week (average temperature, humidity, dominant wind direction).
        If the city is not supported, returns a dictionary with an "error" key and message.
    """
    # city_continent_map = {
    #     "New York": "North America", "Toronto": "North America", "Los Angeles": "North America", "Mexico City": "North America",
    #     "São Paulo": "South America", "Buenos Aires": "South America", "Lima": "South America", "Bogotá": "South America",
    #     "London": "Europe", "Paris": "Europe", "Berlin": "Europe", "Rome": "Europe",
    #     "Tokyo": "Asia", "Beijing": "Asia", "Mumbai": "Asia", "Bangkok": "Asia",
    #     "Cairo": "Africa", "Lagos": "Africa", "Nairobi": "Africa", "Cape Town": "Africa"
    # }

    city_continent_map = supported_cities_search()

    weather_conditions = ["Sunny", "Cloudy", "Rainy", "Stormy", "Snowy", "Windy", "Foggy"]

    if city_name not in city_continent_map:
        return {"error": f"City '{city_name}' is not in the supported list."}

    continent = city_continent_map[city_name]

    temp_ranges = {
        "North America": (10, 25),
        "Europe": (10, 25),
        "Asia": (20, 35),
        "South America": (20, 35),
        "Africa": (25, 45)
    }

    min_temp, max_temp = temp_ranges[continent]

    wind_forecast = []
    temps = []
    humidities = []
    wind_directions = []

    for i in range(7):
        day = datetime.now() + timedelta(days=i)
        temp = round(random.uniform(min_temp, max_temp), 1)
        humidity = random.randint(20, 100)
        wind_dir = random.choice(["N", "NE", "E", "SE", "S", "SW", "W", "NW"])

        wind_data = {
            "date": day.strftime("%Y-%m-%d"),
            "temperature_c": temp,
            "humidity_percent": humidity,
            "condition": random.choice(weather_conditions),
            "wind_speed_kph": round(random.uniform(5, 40), 1),
            "wind_direction": wind_dir
        }

        wind_forecast.append(wind_data)
        temps.append(temp)
        humidities.append(humidity)
        wind_directions.append(wind_dir)

    # Weekly summary
    summary = {
        "average_temperature_c": round(sum(temps) / len(temps), 1),
        "average_humidity_percent": round(sum(humidities) / len(humidities), 1),
        "dominant_wind_direction": Counter(wind_directions).most_common(1)[0][0]
    }

    data = {
        "city": city_name,
        "continent": continent,
        "current_temperature_c": temps[0],
        "current_humidity_percent": humidities[0],
        "current_condition": wind_forecast[0]["condition"],
        "timestamp": datetime.now().isoformat(),
        "weekly_forecast": wind_forecast,
        "weekly_summary": summary
    }

    return data

def event_by_city_search(city_name: str) -> dict:
    """
    Renders a list of cultural events for a supported city. Your response should include a list of events with their details.

    Args:
        city_name (str): The name of the city to get cultural events for.
            Supported cities include major cities from North America, South America, Europe, Asia, and Africa.

    Returns:
        dict: A dictionary containing:
            - city (str): The city name.
            - continent (str): The continent of the city.
            - events (list): A list of event dictionaries, each with:
                - name (str): Event name.
                - date (str): ISO formatted date.
                - type (str): Type of event (e.g., Festival, Concert, Exhibition).
                - location (str): Venue or location.
                - description (str): Short description.
            If the city is not supported, returns a dictionary with an "error" key and message.
    """
    # city_continent_map = {
    #     "New York": "North America", "Toronto": "North America", "Los Angeles": "North America", "Mexico City": "North America",
    #     "São Paulo": "South America", "Buenos Aires": "South America", "Lima": "South America", "Bogotá": "South America",
    #     "London": "Europe", "Paris": "Europe", "Berlin": "Europe", "Rome": "Europe",
    #     "Tokyo": "Asia", "Beijing": "Asia", "Mumbai": "Asia", "Bangkok": "Asia",
    #     "Cairo": "Africa", "Lagos": "Africa", "Nairobi": "Africa", "Cape Town": "Africa"
    # }

    city_continent_map = supported_cities_search()

    event_types = ["Festival", "Concert", "Exhibition", "Parade", "Theater", "Food Fair", "Cultural Workshop"]
    venues = ["City Hall", "Central Park", "Downtown Arena", "Museum of Art", "Opera House", "Riverfront", "Main Square"]

    if city_name not in city_continent_map:
        return {"error": f"City '{city_name}' is not in the supported list."}

    continent = city_continent_map[city_name]
    events = []
    for i in range(5):
        event_date = (datetime.now() + timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")
        event_type = random.choice(event_types)
        venue = random.choice(venues)
        event = {
            "name": f"{city_name} {event_type} {i+1}",
            "date": event_date,
            "type": event_type,
            "location": venue,
            "description": f"A wonderful {event_type.lower()} happening at {venue} in {city_name}."
        }
        events.append(event)

    return {
        "city": city_name,
        "continent": continent,
        "events": events
    }