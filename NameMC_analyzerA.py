#!/usr/bin/env python3
"""
ПОСЛЕДОВАТЕЛЬНЫЙ СБОРЩИК HTML NAMEMC
Скачивает по одному пользователю с проверкой уже скачанного
"""

import time
import csv
import json
import re
import os
from collections import deque
from typing import Set, Tuple, List, Dict, Optional
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

class SequentialDownloader:
    """Последовательный сборщик с проверкой существующих файлов"""

    def __init__(self, download_dir: str = "downloaded_html"):
        self.download_dir = download_dir
        os.makedirs(download_dir, exist_ok=True)
        self.stats = {'downloaded': 0, 'skipped': 0, 'failed': 0}

    def is_already_downloaded(self, username: str, page_type: str) -> bool:
        """Проверяет скачан ли файл"""
        if page_type == 'profile':
            html_path = os.path.join(self.download_dir, f"{username}.html")
        elif page_type == 'followers':
            html_path = os.path.join(self.download_dir, f"{username}_followers.html")
        elif page_type == 'following':
            html_path = os.path.join(self.download_dir, f"{username}_following.html")
        else:
            return False

        if os.path.exists(html_path):
            file_size = os.path.getsize(html_path)
            if file_size > 5000:
                return True
        return False

    def download_page(self, username: str, page_type: str) -> bool:
        """Скачивает одну страницу"""
        if page_type == 'profile':
            url = f"https://namemc.com/profile/{username}.1"
            filepath = os.path.join(self.download_dir, f"{username}.html")
            label = "ПРОФИЛЬ"
        elif page_type == 'followers':
            url = f"https://namemc.com/profile/{username}.1/followers"
            filepath = os.path.join(self.download_dir, f"{username}_followers.html")
            label = "ПОДПИСЧИКИ"
        elif page_type == 'following':
            url = f"https://namemc.com/profile/{username}.1/following"
            filepath = os.path.join(self.download_dir, f"{username}_following.html")
            label = "ПОДПИСКИ"
        else:
            return False

        if self.is_already_downloaded(username, page_type):
            print(f"   {label}: {username} уже есть")
            self.stats['skipped'] += 1
            return True

        print(f"   {label}: {username} скачиваю")

        with sync_playwright() as p:
            browser = p.firefox.launch(headless=False)
            page = browser.new_page()

            try:
                page.goto(url, timeout=30000, wait_until="domcontentloaded")
                time.sleep(2)

                for _ in range(2):
                    page.evaluate("window.scrollBy(0, 500)")
                    time.sleep(0.5)

                html_content = page.content()
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                file_size = os.path.getsize(filepath)
                print(f"      СОХРАНЕНО {file_size} байт")
                self.stats['downloaded'] += 1
                return True

            except Exception as e:
                print(f"      ОШИБКА {e}")
                self.stats['failed'] += 1
                return False
            finally:
                browser.close()

    def download_user_all(self, username: str) -> bool:
        """Скачивает все страницы пользователя"""
        print(f"\nЗАГРУЗКА ДАННЫХ {username}")

        profile_ok = self.download_page(username, 'profile')
        followers_ok = self.download_page(username, 'followers')
        following_ok = self.download_page(username, 'following')

        return profile_ok or followers_ok or following_ok


class SequentialGraphBuilder:
    """Последовательный строитель графа с умной загрузкой"""

    def __init__(self, start_user: str = "_Candu__", max_depth: int = 2, max_users: int = 100):
        self.start_user = start_user
        self.max_depth = max_depth
        self.max_users = max_users
        self.downloader = SequentialDownloader()

        self.all_users = set()
        self.user_followers = {}
        self.user_following = {}
        self.edges = set()
        self.queue = deque()
        self.processed = set()

    def collect_user_data_from_files(self, username: str) -> Tuple[List[str], List[str]]:
        """Загружает данные пользователя из файлов"""
        followers = []
        following = []

        followers_path = os.path.join(self.downloader.download_dir, f"{username}_followers.html")
        following_path = os.path.join(self.downloader.download_dir, f"{username}_following.html")

        if os.path.exists(followers_path):
            try:
                with open(followers_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    match = re.search(r'/profile/([^/?]+)', href)
                    if match:
                        name = match.group(1)
                        name = re.sub(r'\.\d+$', '', name)
                        if name and name != username:
                            followers.append(name)
                followers = list(dict.fromkeys(followers))
            except Exception as e:
                print(f"      ОШИБКА ПАРСИНГА ПОДПИСЧИКОВ {e}")

        if os.path.exists(following_path):
            try:
                with open(following_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f.read(), 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    match = re.search(r'/profile/([^/?]+)', href)
                    if match:
                        name = match.group(1)
                        name = re.sub(r'\.\d+$', '', name)
                        if name and name != username:
                            following.append(name)
                following = list(dict.fromkeys(following))
            except Exception as e:
                print(f"      ОШИБКА ПАРСИНГА ПОДПИСОК {e}")

        return followers, following

    def process_user(self, username: str, depth: int) -> bool:
        """Обрабатывает одного пользователя"""

        print(f"\n{'#'*60}")
        print(f"УРОВЕНЬ {depth}: {username}")
        print(f"{'#'*60}")

        followers, following = self.collect_user_data_from_files(username)

        if not followers and not following:
            print(f"   ДАННЫХ НЕТ СКАЧИВАЮ")
            if not self.downloader.download_user_all(username):
                print(f"   НЕ УДАЛОСЬ СКАЧАТЬ {username}")
                return False
            followers, following = self.collect_user_data_from_files(username)

        self.user_followers[username] = followers
        self.user_following[username] = following
        self.all_users.add(username)
        self.all_users.update(followers)
        self.all_users.update(following)

        print(f"      ПОДПИСЧИКОВ {len(followers)}")
        print(f"      ПОДПИСОК {len(following)}")

        return True

    def build_graph(self):
        """Строит граф последовательным обходом"""

        print("\n" + "="*70)
        print("ПОСЛЕДОВАТЕЛЬНЫЙ СБОРЩИК ГРАФА")
        print("="*70)
        print(f"СТАРТОВЫЙ ПОЛЬЗОВАТЕЛЬ {self.start_user}")
        print(f"МАКСИМАЛЬНАЯ ГЛУБИНА {self.max_depth}")
        print(f"МАКСИМУМ ПОЛЬЗОВАТЕЛЕЙ {self.max_users}")
        print("\nПОРЯДОК РАБОТЫ")
        print("   1 ПРОВЕРКА КАКИЕ ФАЙЛЫ УЖЕ СКАЧАНЫ")
        print("   2 СКАЧИВАНИЕ ТОЛЬКО НЕДОСТАЮЩИХ")
        print("   3 ОБРАБОТКА ПОЛЬЗОВАТЕЛЕЙ ПО ОЧЕРЕДИ")
        print("="*70)

        input("\nНАЖМИТЕ ENTER ДЛЯ СТАРТА")

        self.queue.append((self.start_user, 0))
        self.processed.add(self.start_user)

        processed_count = 0

        while self.queue and processed_count < self.max_users:
            username, depth = self.queue.popleft()

            if depth > self.max_depth:
                print(f"\nДОСТИГНУТА МАКСИМАЛЬНАЯ ГЛУБИНА {self.max_depth} для {username}")
                continue

            processed_count += 1

            if not self.process_user(username, depth):
                continue

            if depth < self.max_depth and len(self.processed) < self.max_users:
                all_connections = set(self.user_followers.get(username, []) + self.user_following.get(username, []))
                new_users = []

                for conn in all_connections:
                    if conn not in self.processed:
                        self.processed.add(conn)
                        self.queue.append((conn, depth + 1))
                        new_users.append(conn)

                if new_users:
                    print(f"\n   ДОБАВЛЕНО В ОЧЕРЕДЬ {depth + 1} УРОВЕНЬ {len(new_users)}")
                    if len(new_users) <= 10:
                        print(f"      {', '.join(new_users)}")

            print(f"\n   ПРОГРЕСС {processed_count}/{self.max_users}")
            print(f"   В ОЧЕРЕДИ {len(self.queue)}")
            print(f"   ВСЕГО ПОЛЬЗОВАТЕЛЕЙ {len(self.all_users)}")

            if self.queue:
                print(f"   ПАУЗА 2 СЕКУНДЫ")
                time.sleep(2)

        self.build_edges()

        print("\n" + "="*70)
        print("ИТОГОВАЯ СТАТИСТИКА")
        print("="*70)
        print(f"ВСЕГО ПОЛЬЗОВАТЕЛЕЙ {len(self.all_users)}")
        print(f"ВСЕГО СВЯЗЕЙ {len(self.edges)}")
        print(f"СКАЧАНО НОВЫХ ФАЙЛОВ {self.downloader.stats['downloaded']}")
        print(f"ПРОПУЩЕНО УЖЕ БЫЛИ {self.downloader.stats['skipped']}")
        print(f"ОШИБОК {self.downloader.stats['failed']}")

    def build_edges(self):
        """Строит рёбра графа"""
        self.edges.clear()

        for user in self.user_followers:
            for follower in self.user_followers[user]:
                self.edges.add((follower, user))

        for user in self.user_following:
            for following in self.user_following[user]:
                self.edges.add((user, following))

    def save_results(self):
        """Сохраняет результаты"""

        print("\nСОХРАНЕНИЕ РЕЗУЛЬТАТОВ")

        with open('graph.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target'])
            for source, target in sorted(self.edges):
                writer.writerow([source, target])
        print(f"   GRAPH_CSV {len(self.edges)} СВЯЗЕЙ")

        node_degrees = {}
        for source, target in self.edges:
            node_degrees[source] = node_degrees.get(source, 0) + 1
            node_degrees[target] = node_degrees.get(target, 0) + 1

        top_users = sorted(node_degrees.items(), key=lambda x: x[1], reverse=True)[:20]

        stats = {
            "total_users": len(self.all_users),
            "total_edges": len(self.edges),
            "start_user": self.start_user,
            "downloaded_files": self.downloader.stats['downloaded'],
            "skipped_files": self.downloader.stats['skipped'],
            "failed_downloads": self.downloader.stats['failed'],
            "top_connected_users": [
                {"username": user, "connections": count}
                for user, count in top_users
            ]
        }

        with open('stats.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        print(f"   STATS_JSON")

        with open('all_users.txt', 'w', encoding='utf-8') as f:
            for user in sorted(self.all_users):
                f.write(f"{user}\n")
        print(f"   ALL_USERS_TXT {len(self.all_users)} ПОЛЬЗОВАТЕЛЕЙ")

        if top_users:
            print(f"\nТОП 10 ПО СВЯЗЯМ")
            print("-" * 60)
            for i, (user, count) in enumerate(top_users[:10], 1):
                print(f"   {i:2} {user:35} {count:3} СВЯЗЕЙ")

    def run(self):
        """Запуск"""
        try:
            self.build_graph()
            self.save_results()

            print("\n" + "="*70)
            print("РАБОТА ЗАВЕРШЕНА")
            print("="*70)
            print("СОЗДАННЫЕ ФАЙЛЫ")
            print("   GRAPH_CSV ДЛЯ GEPHI")
            print("   STATS_JSON СТАТИСТИКА")
            print("   ALL_USERS_TXT СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ")
            print("   DOWNLOADED_HTML ПАПКА С HTML ФАЙЛАМИ")
            print("\nЗАПУСТИТЕ АНАЛИЗАТОР ДЛЯ СОЗДАНИЯ HTML ГРАФА И OBSIDIAN ЗАМЕТОК")
            print("="*70)

        except KeyboardInterrupt:
            print("\n\nПРЕРВАНО СОХРАНЯЮ РЕЗУЛЬТАТЫ")
            self.save_results()


def main():
    print("\n" + "="*70)
    print("ПОСЛЕДОВАТЕЛЬНЫЙ СБОРЩИК ГРАФА NAMEMC")
    print("="*70)
    print("ОСОБЕННОСТИ")
    print("   СКАЧИВАЕТ ПО ОДНОМУ ПОЛЬЗОВАТЕЛЮ")
    print("   ПРОВЕРЯЕТ КАКИЕ ФАЙЛЫ УЖЕ ЕСТЬ")
    print("   СКАЧИВАЕТ ТОЛЬКО НЕДОСТАЮЩИЕ")
    print("   СОБИРАЕТ ПРОФИЛИ ПОДПИСЧИКОВ И ПОДПИСКИ")
    print("="*70)

    start_user = input("\nСТАРТОВЫЙ ПОЛЬЗОВАТЕЛЬ ENTER ДЛЯ _Candu__: ").strip()
    start_user = start_user if start_user else "_Candu__"

    max_depth = input("МАКСИМАЛЬНАЯ ГЛУБИНА 1-2 ENTER ДЛЯ 2: ").strip()
    max_depth = int(max_depth) if max_depth else 2

    max_users = input("МАКСИМУМ ПОЛЬЗОВАТЕЛЕЙ ENTER ДЛЯ 100: ").strip()
    max_users = int(max_users) if max_users else 100

    builder = SequentialGraphBuilder(
        start_user=start_user,
        max_depth=max_depth,
        max_users=max_users
    )

    builder.run()


if __name__ == "__main__":
    main()