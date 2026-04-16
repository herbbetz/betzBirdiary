import requests
from typing import Dict, List, Tuple


class StationCountClient:
    def __init__(self, url: str, timeout: int = 15):
        self.url = url
        self.timeout = timeout

    def fetch_json(self) -> Dict:
        response = requests.get(self.url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def extract_date_sum(self, data: Dict) -> List[Tuple[str, int]]:
        count_data = data.get("count", {})
        result: List[Tuple[str, int]] = []

        for date_str, entry in count_data.items():
            sum_value = entry.get("sum", 0)
            result.append((date_str, sum_value))

        result.sort(key=lambda x: x[0])
        return result

    def get_date_sum(self) -> List[Tuple[str, int]]:
        data = self.fetch_json()
        return self.extract_date_sum(data)

    def as_csv(self) -> str:
        rows = self.get_date_sum()
        lines = ["Datum,Summe"]
        for date_str, sum_value in rows:
            lines.append(f"{date_str},{sum_value}")
        return "\n".join(lines)


if __name__ == "__main__":
#    url = "https://wiediversistmeingarten.org/api/station/0dd85062-ec97-4c64-bd81-70d4c932295e"
#    url = "https://wiediversistmeingarten.org/api/station/f2ac2e34-7067-4275-8d55-440001852513"
    url = "https://wiediversistmeingarten.org/api/station/87bab185-7630-461c-85e6-c04cf5bab180"
    client = StationCountClient(url)

    try:
        rows = client.get_date_sum()
        print("Datum       | Summe")
        print("-------------------")
        for date_str, sum_value in rows:
            print(f"{date_str} | {sum_value}")

        print("\nCSV:\n")
        print(client.as_csv())

    except requests.RequestException as e:
        print(f"Fehler beim Laden der Daten: {e}")
