from collections import defaultdict, OrderedDict
from datetime import datetime, timedelta

from base_models.wits_models import Wits_user as users


# todo Добавить logger


def sort_by_month(date: str):
    """Передаём сюда дату в формате October 2017"""
    return datetime.strptime(date, '%B %Y')


class Meta:
    def __repr__(self):
        return '<class.{}({})>'.format(self.__class__.__name__, self.__str__())


class User(Meta):
    def __init__(self, id, session):
        self.id = id
        self.param = session.query(users).filter_by(id=id).first()
        self.last_name = self.param.last_name
        self.first_name = self.param.first_name
        self.patr_name = self.param.patr_name
        self._sessions = {}
        self.opened_session = []
        self._logged = False
        self.total_video_time = defaultdict(int)
        self.total_monitoring_time = defaultdict(int)
        self._collisions = []

    def __str__(self):
        return '{}.{}'.format(self.fio, bool(self.is_logged))

    @property
    def fio(self):
        return ' '.join(str(i) for i in [self.last_name, self.first_name, self.patr_name] or [self.param.name] if i)

    def info(self):
        return '{id}\n{org}\n{pos} \n{name}'.format(id=self.id,
                                                    pos=self.param.position,
                                                    name=self.fio,
                                                    org=self.param.organization)

    @property
    def is_logged(self):
        return self.active

    @property
    def collision_sessions(self):
        return self._collisions

    @collision_sessions.setter
    def collision_sessions(self, ses: str):
        ses = ses.replace('!', ' ').replace('=', ' ').split()[0]
        self._collisions.append(ses)

    @property
    def active(self):
        return self.opened_session

    @active.setter
    def active(self, session: object):
        self.active.append(session)

    def sessions(self, ses: str):
        try:
            session = self._sessions[ses]
        except KeyError:
            session = self._sessions[ses] = Session(ses)
        return session

    def session_start(self, session: str, dt: int):
        session = self.sessions(session)
        assert not session.status, 'Пытаемся открыть уже открутую сессию! {}'.format(session)
        session.open(dt)
        self.active.append(session)

    def session_stop(self, session: str, dt: int):
        active_session = self.get_active_session()
        new_session = self.sessions(session)
        if active_session is not new_session:
            print('[INFO]Сессия на закрытие не соответствует активной сессии\n'
                  'user: {}\n'
                  'active: {}\n'
                  'new_session: {}'.format(self.info(), active_session, new_session))
            print('[INFO]Игнорируем Сессию {}!!\n'.format(new_session))
            self.collision_sessions = session
            return None
        assert active_session.status, 'Пытаемся закрыть сессию. Сессия уже закрыта! {}'.format(active_session)
        args_to_close_planshet = '{}=fclose='.format(dt)
        self.session_store(active_session.ses, dt, args_to_close_planshet)
        active_session.close(dt)
        self.active.remove(active_session)

    def session_store(self, session: str, date, args: str):
        active_session = self.get_active_session()
        if active_session.ses != session:
            # Ищем старую закрытую сессию, не открываем её, но записываем в неё отдельно!
            print('[INFO]Не можем записать в сессию {}! Данная сесия не является активной! Активаная сессия: {}'.
                  format(session, active_session))
            if session not in self._sessions:
                print('[WARN]Данной сессии нет у пользователя! Игнорируем...')
                return None
            else:
                old_session = self.sessions(session)
                print('[INFO]У пользователя найдена сессия {}! Сохраняем данные в неё!'.format(old_session))
                old_session.store(date, args)
        else:
            active_session.store(date, args)

    def get_active_session(self):
        session = self.active
        assert len(session) == 1, 'Активной дожна быть только одна сессия! Найдено актиных сессий: ' \
                                  '\n{} ' \
                                  '\nДля пользователя: ' \
                                  '\n{}'.format(session, self.info())
        return session[-1]

    def close_active_session(self, dt=None):
        active_session = self.get_active_session()
        if not dt:
            dt = active_session.get_cached_date()
        self.session_stop(active_session.ses, dt)

    def calculate_total(self):
        for ses in self._sessions.values():
            self.total_video_time[ses.month] += ses.total_time_video.to_timestamp()
            self.total_monitoring_time[ses.month] += ses.total_time.to_timestamp()
            # Сортируем ключи по месяцам и записывам в виде "Месяц":{времяы}
        self.total_video_time = OrderedDict({k: Dt(v) for k, v in sorted(self.total_video_time.items(),
                                                                         key=lambda x: sort_by_month(x[0]))})
        self.total_monitoring_time = OrderedDict({k: Dt(v) for k, v in sorted(self.total_monitoring_time.items(),
                                                                              key=lambda x: sort_by_month(x[0]))})


class Session(Meta):
    def __init__(self, data):
        self.ses = data
        self.total_time = Dt(0)
        self.total_time_video = Dt(0)
        self.planshet = defaultdict(int)
        self.active = False
        self.cached_data = {'start_session': 0, 'last': 0}
        self.storage = {'all': {'total': 0}, 'video': {'start': 0, 'stop': 0}}

    def __str__(self):
        return '{}.{}.{}|total:{}'.format(self.ses,
                                          self.active,
                                          self.cached_data['start_session'],
                                          self.total_time)

    def __eq__(self, other):
        if not isinstance(other, Session):
            return False
        else:
            if self.ses == other.ses:
                return True
            else:
                return False

    @property
    def status(self):
        """
        Возвращает True/False для открытой и закрытой сесси
        :return: Bool 
        """
        return self.active

    @property
    def month(self):
        return Dt.to_report(self.cached_data['start_session'], self.cached_data['last'])

    def close(self, dt):
        self.cached_data['last'] = dt
        last = self.cached_data['last']
        start = self.cached_data['start_session']
        assert last >= start, 'В результате вычитания получился отрицательный результат,' \
                              ' что не возможно для времени!\n {} > {} \nsession: {}'.format(last, start, self.ses)
        self.total_time += last - start
        self.active = False

    def open(self, dt):
        self.cached_data['start_session'] = dt
        self.cached_data['last'] = dt
        self.active = True

    def store(self, dt, args: str):
        def calculate(first, last):
            assert last >= first, 'В результате вычитания получился отрицательный результат,' \
                                  ' что не возможно для времени!\n {} > {} \nsession: {}'.format(last, first, self.ses)
            total = last - first
            self.total_time_video += total
            self.storage['video']['stop'], self.storage['video']['start'] = 0, 0

        time, action, *form = args.split('=')
        # todo Придумать решение для это коллизии!!
        # В информации о сессии хранится время большее, чем в самом логе
        # time = Dt(time)
        # if not time.__ge__(self.storage['video']['start']):
        #     dt = time
        #####################################################################
        form = ''.join(form)
        if not form:
            form = 'Camera'  # для закрытия всех планшетов при закрытии сессии
        if form.startswith('Camera'):
            start = self.storage['video']['start']
            stop = self.storage['video']['stop']
            if action == 'fopen' and not start:
                self.storage['video']['start'] = dt
            elif action == 'fclose' and start:
                calculate(start, dt)
            elif action == 'fopen' and not stop:
                calculate(start, dt)
                self.storage['video']['start'] = dt
                # Остальные формы игнорим.
                # todo сделать подсчёт по всем формам
        self.cached_data['last'] = dt

    def get_cached_date(self):
        return self.cached_data['last'] or self.cached_data['start_session']

    def return_total_time(self):
        return self.total_time

    def return_total_video_time(self):
        return self.total_time_video

    def session_period(self):
        return '{} - {}'.format(self.cached_data['start_session'], self.cached_data['last'])


class Dt(Meta):
    formats = {'date': '%Y-%m-%d', 'datetime': '%Y-%m-%d %H:%M:%S'}

    def __init__(self, dt):
        if isinstance(dt, Dt):
            self.dt = dt.to_timestamp()
        elif isinstance(dt, int):
            if len(str(dt)) > 10:
                dt = int(str(dt)[:10])
            self.dt = dt
        elif isinstance(dt, datetime):
            self.dt = int(datetime.timestamp(dt))
        elif isinstance(dt, str):
            if dt.isdigit():
                self.dt = int(dt[:10])
            elif len(dt) > 10:
                self.dt = datetime.strptime(dt, Dt.formats['datetime']).timestamp()
                self.dt = int(self.dt)
            else:
                self.dt = datetime.strptime(dt, Dt.formats['date']).timestamp()
                self.dt = int(self.dt)
        else:
            exit('Не получилось распознать dt {}, type({})'.format(dt, type(dt)))

    def __str__(self):
        year = Dt('2000-01-01').to_timestamp()
        return self.to_string() if self.dt > year else self.to_human()

    def __float__(self):
        return float(self.dt)

    def __sub__(self, other):
        if isinstance(other, Dt):
            other = other.dt
        return Dt(self.dt - other)

    def __int__(self):
        return self.to_timestamp()

    def __add__(self, other):
        if isinstance(other, Dt):
            other = other.dt
        elif isinstance(other, str) and other.isdigit():
            other = int(other)
        return Dt(self.dt + other)

    def __ge__(self, other):
        if isinstance(other, Dt):
            other = other.dt
        return self.dt >= other

    def to_string(self):
        return datetime.fromtimestamp(self.dt).strftime(Dt.formats['datetime'])

    def to_timestamp(self):
        return int(self.dt)

    def to_request(self):
        return self.to_timestamp() * 1000

    def to_human(self):
        return str(timedelta(seconds=self.dt))  # + ' с'

    @staticmethod
    def to_report(dt_1: int, dt_2=0):
        """Возвращаем месяц и год для сессии"""
        if isinstance(dt_1, int):
            dt_1 = Dt(dt_1)
        if isinstance(dt_2, int):
            dt_2 = Dt(dt_2)
        start = dt_1.dt
        stop = dt_2.dt
        median = (start + stop) / 2
        dt = datetime.fromtimestamp(median)
        return dt.strftime('%B %Y')
