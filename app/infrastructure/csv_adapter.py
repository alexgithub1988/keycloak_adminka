import csv
import os


class CsvAdapter:
    def __init__(self) -> None:
        """Ничего тут не делаем"""
        pass

    def get_list_dicts(self, filename: str) -> list[dict]:
        """Читаем из файла пишем лист словарей"""
        list_of_dicts = []
        with open(filename, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                list_of_dicts.append(row)

        return list_of_dicts

    def dicts_to_csv(
        self,
        dicts: list[dict],
        fieldnames: list,
        filepath: str,
        filename: str = "output.csv",
    ):
        """Из списка словарей пишем в csv"""
        file_path = os.path.join(filepath, filename)
        with open(file_path, "w", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore",
                restval="",
                quoting=csv.QUOTE_ALL,
            )
            writer.writeheader()

            writer.writerows(dicts)
