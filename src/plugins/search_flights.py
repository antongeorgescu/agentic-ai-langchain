import os
import certifi
import requests
import pycountry
import json
import pycountry

from serpapi import GoogleSearch

os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
google_search_api_key = os.getenv("GOOGLE_API_KEY")

def get_my_country():
  """
  Fetches the user's country based on their IP address using ipinfo.io.
  """
  try:
      response = requests.get('https://ipinfo.io/json')
      response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
      data = response.json()
      country = data.get('country')
      if country:
          return country
      else:
          return "Country information not found in the response."
  except requests.exceptions.RequestException as e:
      return f"Error connecting to IP geolocation service: {e}"
  except ValueError:
      return "Error parsing JSON response."

def get_root_directory():
  """
  Returns the root directory of the current project.
  """
  return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

def get_iata_codes_by_country(country_name: str):
    json_path=f"{get_root_directory()}/src/plugins/airports_by_country.json"
    with open(json_path, "r", encoding="utf-8") as f:
        airports = json.load(f)
    return [airport["iata_code"] for airport in airports if airport["country"].lower() == country_name.lower()]

def get_iata_code_by_city(city: str):
    json_path=f"{get_root_directory()}/src/plugins/airports_by_country.json"
    with open(json_path, "r", encoding="utf-8") as f:
        airports = json.load(f)
    return [airport["iata_code"] for airport in airports if airport["city"].lower() == city.lower()]

def get_flight_info(from_city: str = None, to_city: str = None, outbound_date: str = None, return_date: str = None) -> dict:
    """
    Fetches flight information using the Google Flights API.
    If any required parameter is missing, returns an appropriate message.
    """
    
    try:
        missing = []
        if not from_city:
            # Get the departure country from the user's IP address
            from_country = get_my_country()
            city = get_iata_codes_by_country(from_country)
            if city is None:
                missing.append("departure city")
            else:
                return f"[Flight Agent] You seem to be located in {city}. Please provide your departure city."
        if not to_city:
            missing.append("destination city")
        if not outbound_date:
            missing.append("outbound (departure) date")
        if not return_date:
            missing.append("return date")
        if missing:
            return f"[Flight Agent] Unable to process your request. Please provide the following information: {', '.join(missing)}."

        departure_airport = get_iata_code_by_city(from_city)
        if not departure_airport:
            raise ValueError(f"No IATA codes found for country: {from_city}")

        arrival_airport = get_iata_code_by_city(to_city)
        if not arrival_airport:
            raise ValueError(f"No IATA codes found for country: {to_city}")

        params = {
            "engine": "google_flights",
            "hl": "en",
            "departure_id": departure_airport,
            "arrival_id": arrival_airport,
            "outbound_date": outbound_date,
            "return_date": return_date,
            "currency": "USD",
            "type": "1",
            "api_key": google_search_api_key
        }
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        return results
    except Exception as e:
        return f"[Flight Agent] An error occurred while fetching flight information: {str(e)}. Please submit your query again."

if __name__ == "__main__":
  country_code = get_my_country()
  if country_code:
      print(f"You appear to be in the country with code: {country_code}")

      # You can use the `pycountry` library to get the full country name
      # if you have the country code.
      # pip install pycountry
      try:
          
          departure_country = pycountry.countries.get(alpha_2=country_code)
          if departure_country:
              print(f"Full country name: {departure_country.name}")
      except ImportError:
          print("Install 'pycountry' (pip install pycountry) for full country names.")
      except Exception as e:
          print(f"Error getting full country name: {e}")

  codes = get_iata_codes_by_country(departure_country.name)
  if not codes:
      print(f"No IATA codes found for country: {departure_country}")
      exit(1)
  departure_airport = codes[0]  # Use the first IATA code for departure

  arrival_country = "India"  # Example: hardcoded for testing
  codes = get_iata_codes_by_country(arrival_country)
  if not codes:
      print(f"No IATA codes found for country: {arrival_country}")
      exit(1)
  arrival_airport = codes[0]

  params = {
    "engine": "google_flights",
    "hl": "en",
    # "gl": "en",
    "departure_id": departure_airport,
    "arrival_id": arrival_airport,
    "outbound_date": "2025-11-05",
    "return_date": "2025-11-21",
    "currency": "USD",
    "type": "1",
    "api_key": google_search_api_key
  }

  search = GoogleSearch(params)
  results = search.get_dict()

  print(results)