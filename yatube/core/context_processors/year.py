import datetime as dt


def year(request):
    '''
    Функция определяет текущий год
    и помещает его в словарь под ключом year
    '''
    year_now = int(dt.datetime.today().year)
    return {
        'year': year_now
    }
