import requests

BASE_URL = "http://localhost:8000"

def test_root():
    response = requests.get(f"{BASE_URL}/")
    print(f"Root endpoint: {response.status_code}")
    print(response.json())
    print()

def test_meat_types():
    response = requests.get(f"{BASE_URL}/products/meat-types")
    print(f"Meat types endpoint: {response.status_code}")
    if response.status_code == 200:
        print(response.json())
    else:
        print(response.text)
    print()

def test_search():
    response = requests.get(f"{BASE_URL}/products/")
    print(f"Search endpoint: {response.status_code}")
    if response.status_code == 200:
        print(response.json())
    else:
        print(response.text)
    print()

if __name__ == "__main__":
    test_root()
    test_meat_types()
    test_search() 