# -*- coding: utf-8 -*-
"""
Скрипт для загрузки торрентов из RSS nyatorrents
Требуется установленый  торент-клиент Transmission!

"""

import sys, os, time
import logging
from xml.dom.minidom import *
import urllib
import subprocess
import shlex

""" Config """
#path
main_path    = "/home/user/python/DlTorrents/"
targets_dir  = "targets"  #папка с целями 
torrents_dir = "torrents" #папка с торентами
status_dir   = "status"   #здесь храним ссылки уже скаченных торентов
log_dir      = "log"

#Download
timeout = 2     # таймаут между скачеванием торентов

#Transmission
trm_login_pass = 'torradmin:torrpass' #transmission login:password
"""end config"""

#Собираем полный путь путь
targets_dir = os.path.join(main_path,targets_dir)
torrents_dir = os.path.join(main_path,torrents_dir)
status_dir = os.path.join(main_path,status_dir)
log_dir = os.path.join(main_path,log_dir)

#Настройка логов
logging.basicConfig(format=u'%(levelname)-8s [%(asctime)s] %(message)s', level=logging.DEBUG, filename=os.path.join(log_dir, 'main.log'))


#
def run_targets(name,link):
    logging.info(u'Цель - ' + name + u' Aдрес - ' + link[:-1])

    #проверить есть ли папка под цель
    #if not os.path.isdir(os.path.join(status_dir,name)):
    #    logging.info( u"Не найдена папка для цели - " +name+ u". Создаём...")
    #    os.mkdir(os.path.join(status_dir,name))

    file_rss = os.path.join(status_dir, 'rss.xml')
    file_dl  = os.path.join(status_dir, name)

    if not os.path.isfile(file_dl):
        f = open(file_dl, 'w')
        f.write('')
        f.close()

    #загрузить RSS по ссылке, в файл <имя_цели>/rss.xml
    urllib.urlretrieve(link, file_rss)
    time.sleep(timeout)

    #вытащить ссылки из RSS
    xml = parse(file_rss)
    links = xml.getElementsByTagName('link')

    #загрузить ссылки из файла status/<имя_цели>/dl_links
    dld_links = []
    for line in open(file_dl):
        dld_links.append(line[0:-1]) #берём всю строчку без \n

    #загрузить торенты по новым ссылкам, которых нет в файле  
    dl = []
    for node in links[1:]:       # не берём первую ссылку (там ссылка на сайт)
        lnk = node.childNodes[0].nodeValue
        if not (lnk in dld_links):
            dl.append(lnk)

    #добавляем новые ссылки в файл (чтоб повторно не качать)
    f = open(file_dl, 'a')
    for ln in dl:
        f.write(ln+'\n')
    f.close()
    #возвращаем список файлов для загрузки
    return dl


if not os.path.isdir(targets_dir):
    logging.critical(u"Ошибка! Не найдена папка с целями! \n Завершаем работу.")
    sys.exit()

if not os.path.isdir(torrents_dir):
    logging.info(u"Не найдена папка с торентами! Создаём...")
    os.mkdir(torrents_dir)

if not os.path.isdir(status_dir):
    logging.info(u"Не найдена папка для храниния иформации о скаченных торентах! Создаём...")
    os.mkdir(status_dir)

if not os.path.isdir(log_dir):
    logging.info(u"Не найдена папка для записи логов! Создаём...")
    os.mkdir(log_dir)

logging.debug(u"Загрузка списка целей ...")
for files in os.listdir(targets_dir):
    if not files[0] == '.' and not files[-1] == '~':
        f = open(os.path.join(targets_dir, files))
        trg_name = files
        trg_link = f.readline()
        f.close()
        dl_link = run_targets(trg_name, trg_link)

        logging.debug(u'Загружена цель: ' + trg_name)
        count = 0
        for link in dl_link:
            logging.debug(u'Загрузка торрента: ' + link)
            urllib.urlretrieve( link, os.path.join(torrents_dir, trg_name+'-'+str(count)+'.torrent'))
            time.sleep(timeout)
            count += 1

#передаём скаченные торенты в трансмииссион
for fl in os.listdir(torrents_dir):
    cmd = 'transmission-remote -a ' + os.path.join(torrents_dir, fl)+' -n ' + trm_login_pass
    args = shlex.split(cmd)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    result = p.communicate()[0]

    #удалить торрент если он успешно добавлен или уже был добавлен
    if result.find('success') != -1:
        logging.info(u'Торент успешно добавлен ' + fl)
        os.remove(os.path.join(torrents_dir, fl))
    elif result.find('duplicate torrent') != -1:
        logging.info(u'Торент уже был добавлен! ' + fl)
        os.remove(os.path.join(torrents_dir, fl))
    elif result.find('invalid') != -1:
        logging.error(u'Ошибка! Некоректный торент файл! ' + fl)
        os.remove(os.path.join(torrents_dir, fl))
    else:
        logging.critical(u'Ошибка! Торент не добавлен ' + fl)
