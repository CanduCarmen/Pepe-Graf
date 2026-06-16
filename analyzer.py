!/usr/bin/env python3
"""
Анализатор HTML файлов NameMC
Строит граф связей между пользователями
"""

import os
import re
import csv
import json
from pathlib import Path
from datetime import datetime
from typing import Set, Dict
from collections import defaultdict
from bs4 import BeautifulSoup

class NameMCObsidianAnalyzer:
    """Анализатор для построения графа"""

    def __init__(self, html_dir: str = "downloaded_html"):
        self.html_dir = Path(html_dir)
        self.user_followers = defaultdict(set)
        self.user_following = defaultdict(set)
        self.all_users = set()
        self.all_edges = set()

    def parse_followers(self, html_path: Path, current_user: str) -> list:
        """Парсит подписчиков из HTML"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
        except:
            return []

        followers = []
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            match = re.search(r'/profile/([^/?]+)', href)
            if match:
                name = match.group(1)
                name = re.sub(r'\.\d+$', '', name)
                if name and name != current_user:
                    followers.append(name)

        return list(dict.fromkeys(followers))

    def parse_following(self, html_path: Path, current_user: str) -> list:
        """Парсит подписки из HTML"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
        except:
            return []

        following = []
        links = soup.find_all('a', href=True)
        for link in links:
            href = link.get('href', '')
            match = re.search(r'/profile/([^/?]+)', href)
            if match:
                name = match.group(1)
                name = re.sub(r'\.\d+$', '', name)
                if name and name != current_user:
                    following.append(name)

        return list(dict.fromkeys(following))

    def parse_all(self):
        """Парсит все HTML файлы"""
        print("\nСканирование HTML файлов...")

        html_files = list(self.html_dir.glob("*.html"))
        if not html_files:
            print(f"Ошибка: нет HTML файлов в {self.html_dir}")
            return False

        print(f"   Найдено файлов: {len(html_files)}")

        print("\nПарсинг связей...")
        for html_file in html_files:
            name = html_file.stem

            if name.endswith('_followers'):
                user = name[:-10]
                followers = self.parse_followers(html_file, user)
                if followers:
                    self.user_followers[user].update(followers)
                    self.all_users.add(user)
                    self.all_users.update(followers)
                    for follower in followers:
                        self.all_edges.add((follower, user))

            elif name.endswith('_following'):
                user = name[:-10]
                following = self.parse_following(html_file, user)
                if following:
                    self.user_following[user].update(following)
                    self.all_users.add(user)
                    self.all_users.update(following)
                    for follow in following:
                        self.all_edges.add((user, follow))

        print(f"\n   Всего пользователей: {len(self.all_users)}")
        print(f"   Всего связей: {len(self.all_edges)}")
        return True

    def generate_obsidian_notes(self, output_dir: Path):
        """Генерирует Obsidian заметки для всех пользователей"""
        print(f"\nГенерация Obsidian заметок для {len(self.all_users)} пользователей...")

        notes_dir = output_dir / "obsidian_notes"
        notes_dir.mkdir(exist_ok=True)

        node_degree = defaultdict(int)
        for source, target in self.all_edges:
            node_degree[source] += 1
            node_degree[target] += 1

        index_path = output_dir / "README.md"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write("# NameMC Социальный Граф\n\n")
            f.write(f"Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Статистика\n\n")
            f.write(f"- Всего пользователей: {len(self.all_users)}\n")
            f.write(f"- Всего связей: {len(self.all_edges)}\n\n")

            f.write("## Все пользователи\n\n")
            f.write("| Пользователь | Связей |\n")
            f.write("|-------------|--------|\n")

            for user in sorted(self.all_users):
                connections = node_degree.get(user, 0)
                f.write(f"| [[{user}]] | {connections} |\n")

        print(f"   готово: {index_path.name}")

        user_count = 0
        for user in sorted(self.all_users):
            user_count += 1
            note_path = notes_dir / f"{user}.md"

            namemc_link = f"https://namemc.com/profile/{user}.1"
            connections = node_degree.get(user, 0)

            with open(note_path, 'w', encoding='utf-8') as f:
                f.write("---\n")
                f.write(f"aliases: [{user}]\n")
                f.write(f"tags: [minecraft, player]\n")
                f.write(f"connections: {connections}\n")
                f.write(f"namemc: {namemc_link}\n")
                f.write("---\n\n")

                f.write(f"# {user}\n\n")
                f.write(f"[{user}]({namemc_link})\n\n")

                followers = self.user_followers.get(user, set())
                following = self.user_following.get(user, set())

                if followers or following:
                    f.write(f"## Связи\n\n")
                    f.write(f"- Всего связей: {connections}\n")
                    f.write(f"- Подписчиков: {len(followers)}\n")
                    f.write(f"- Подписок: {len(following)}\n\n")

                    if followers:
                        f.write(f"### Подписчики\n\n")
                        for follower in sorted(followers)[:50]:
                            f.write(f"- [[{follower}]]\n")
                        if len(followers) > 50:
                            f.write(f"- ... и ещё {len(followers) - 50}\n")
                        f.write("\n")

                    if following:
                        f.write(f"### Подписки\n\n")
                        for follow in sorted(following)[:50]:
                            f.write(f"- [[{follow}]]\n")
                        if len(following) > 50:
                            f.write(f"- ... и ещё {len(following) - 50}\n")
                        f.write("\n")

            if user_count % 100 == 0:
                print(f"      Создано {user_count} заметок...")

        print(f"   готово: создано {user_count} заметок в {notes_dir}")

    def generate_top_users_txt(self, output_dir: Path):
        """Генерирует топ пользователей по количеству связей"""
        print(f"\nГенерация топа пользователей...")

        node_degree = defaultdict(int)
        for source, target in self.all_edges:
            node_degree[source] += 1
            node_degree[target] += 1

        sorted_users = sorted(node_degree.items(), key=lambda x: x[1], reverse=True)

        top_path = output_dir / "top_users.txt"
        with open(top_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("ТОП ПОЛЬЗОВАТЕЛЕЙ ПО КОЛИЧЕСТВУ СВЯЗЕЙ\n")
            f.write("=" * 80 + "\n")
            f.write(f"Всего пользователей: {len(node_degree)}\n")
            f.write(f"Всего связей: {len(self.all_edges)}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"{'N':<5} {'Пользователь':<35} {'Связей':<8}\n")
            f.write("-" * 80 + "\n")

            for i, (user, degree) in enumerate(sorted_users, 1):
                f.write(f"{i:<5} {user:<35} {degree:<8}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("Топ-10:\n")
            f.write("=" * 80 + "\n")
            for i, (user, degree) in enumerate(sorted_users[:10], 1):
                f.write(f"{i:2}. {user} - {degree} связей\n")

        print(f"   готово: {top_path.name}")

    def run(self):
        """Запуск анализа"""
        if not self.parse_all():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(f"namemc_graph_{timestamp}")
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nПапка: {output_dir}")

        self.generate_top_users_txt(output_dir)
        self.generate_obsidian_notes(output_dir)

        with open(output_dir / "all_users.txt", 'w', encoding='utf-8') as f:
            for user in sorted(self.all_users):
                f.write(f"{user}\n")

        print(f"\n   готово: all_users.txt (все {len(self.all_users)} пользователей)")

        # Сохраняем граф в CSV для Gephi
        with open(output_dir / "graph.csv", 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['source', 'target'])
            for source, target in sorted(self.all_edges):
                writer.writerow([source, target])
        print(f"   готово: graph.csv ({len(self.all_edges)} связей)")

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)
        print(f"\nИТОГИ:")
        print(f"   Пользователей: {len(self.all_users)}")
        print(f"   Связей: {len(self.all_edges)}")
        print(f"\nФАЙЛЫ в {output_dir}:")
        print(f"   top_users.txt - рейтинг пользователей")
        print(f"   all_users.txt - список всех пользователей")
        print(f"   graph.csv - граф для Gephi")
        print(f"   obsidian_notes/ - заметки Obsidian")
        print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("АНАЛИЗАТОР ГРАФА NAMEMC")
    print("=" * 60)
    print("   Строит граф связей между пользователями")
    print("   Не собирает социальные сети")
    print("=" * 60)

    html_dir = input("\nПуть к папке с HTML (Enter для 'downloaded_html'): ").strip()
    if not html_dir:
        html_dir = "downloaded_html"

    if not os.path.exists(html_dir):
        print(f"\nОшибка: папка '{html_dir}' не найдена")
        return

    analyzer = NameMCObsidianAnalyzer(html_dir=html_dir)
    analyzer.run()


if __name__ == "__main__":
    main()
