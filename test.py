import requests, json

url = 'https://restcountries.com/v3/all'
records = []

response = requests.get(url, verify=False)
json_data = json.dumps(response.json())

countries = json.loads(json_data)
# print(countries)

for country in countries:
    name = country["name"]["official"]
    population = country["population"]
    area = country["area"]
    records.append({"name": name, "population": population, "area": area})

print(records)

# "name" 하위의 "official" 값 추출
# official_name = data["name"]["official"]