#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from __future__ import print_function

import sys
import path
import datetime
# todo прикрутить argparse


def docs(script_name, help=False):
    if help:
        print('{n}{script_name} {n}'.format(script_name=script_name, n='\n'))
        print(main.__doc__)
        print('USAGE: puthon {} {}'.format(script_name, ' '.join(['{some_dir}', '{dest_dir}'])))
    else:
        print('USAGE: puthon {} {}'.format(script_name, ' '.join(['{some_dir}', '{dest_dir}'])))
    exit(0)


def check_input_args(*args):
    """
    :param args: Список аргуменов переданных скрипту
    :return:
        store - object:Path(откуда)
        dest - object:Path(куда)
        move - bool:True/False
    """
    script_name = args[0]
    for arg in args:
        if arg in ['-h', '--help']:
            docs(script_name, True)

    store = path.Path(args[1])
    dest = path.Path(args[2])
    move = True if args[3] == 'move' else False
    if not store.isdir():
        exit('Каталог c архивом по пути: "{}" не найден! Выходим'.format(store))
    return store, dest, move


def check_dest_path(dest):
    if dest.islink():
        dest = dest.readlinkabs()

    if not dest.isdir():
        exit('Указанный пусть назначения не существует! Проверьте путь {}!'.format(dest))
    elif not path.Path('/media/hdd').ismount():
        exit('Проверьте mount hdd /media/hdd!')


def get_datetime(file_name):
    dt = datetime.datetime.strptime(file_name[:16], '%Y%m%d_%H%M%S_')
    return dt.date(), dt.time()


def print_progress_bar(iteration, total, file_name, prefix='', suffix='', decimals=3, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        record      - Required  : current record (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(
        '\rFile {} | Current iteration : {} | Max: {} | {} |{}| {}% {}'.format(file_name, iteration, total,
                                                                               prefix, bar, percent,
                                                                               suffix),
        end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()


def main():
    """
Скрипт для переноса восстановленного архива из общего хранилища по папкам.
Принимает:
{Первой переменной} : Путь до восстановленного архива
{Второй переменной} : Путь куда перенести архив создав новое древо подобно коннекту {date}/{hour}/{file}
{Третьей переменной}: Опционально можду указать 'move/copy' для того чтобы мувать файлы. Иначе копирует.
"""

    file_pattern = '*.flv'

    store, dest, move = check_input_args(*sys.argv)
    check_dest_path(dest)
    total = len([i for i in store.walk(file_pattern)]) - 1
    print_progress_bar(0, total, '', prefix='Progress', suffix='Complete', length=50)
    for i, file in enumerate(store.walk(file_pattern)):
        path_to_new_store = dest
        date, time = get_datetime(file.name)
        date = date.isoformat()
        hour = time.isoformat()[:2]
        path_to_new_store = path_to_new_store + date + '/'
        if not path_to_new_store.exists():
            path_to_new_store.mkdir()
        path_to_new_store = path_to_new_store + hour + '/'
        if not path_to_new_store.exists():
            path_to_new_store.mkdir()
        if (path_to_new_store + file.name).exists():
            if (path_to_new_store + file.name).read_md5() == file.read_md5():
                print('File {} already exist in destination directory. Skipping..'.format(file.name))
                continue
        try:
            if move:
                file.move(path_to_new_store)
            else:
                file.copy(path_to_new_store)
        except Exception:
            print('File {} already exist in destination directory. Skipping..'.format(file.name))
            continue
        print_progress_bar(i, total, file.name, prefix='Progress', suffix='Complete', length=50)


if __name__ == '__main__':
    main()
