import csv



class CsvAdapter:

    def __init__(self):
        pass




    def get_list_dicts(self,filename):
        """ Читаем из файла пишем лист словарей"""
        list_of_dicts = []
        with open(filename, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                list_of_dicts.append(row)

        return list_of_dicts





