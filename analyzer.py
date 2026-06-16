#!/usr/bin/env python3
"""
Анализатор HTML файлов NameMC
Собирает Telegram и Steam всех пользователей в отдельный файл
"""

import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Set, Dict
from collections import defaultdict
from bs4 import BeautifulSoup

class NameMCObsidianAnalyzer:
    """Анализатор с генерацией Obsidian заметок без Discord"""

    def __init__(self, html_dir: str = "downloaded_html"):
        self.html_dir = Path(html_dir)
        self.user_followers = defaultdict(set)
        self.user_following = defaultdict(set)
        self.all_users = set()
        self.all_edges = set()
        self.user_socials = {}
        self.user_skins = {}

    def extract_socials_and_skin(self, html_path: Path, username: str):
        """Извлекает соцсети кроме Discord и скин из HTML профиля"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
        except:
            return

        socials = {}
        all_links = soup.find_all('a', href=True)

        for link in all_links:
            href = link.get('href', '')
            if 'discord' in href.lower() or 'discord.gg' in href.lower():
                continue
            elif 'github.com' in href.lower():
                socials['github'] = href
            elif 'steamcommunity.com' in href.lower():
                socials['steam'] = href
            elif 't.me' in href.lower() or 'telegram' in href.lower():
                tg_match = re.search(r't\.me/([^/?]+)', href)
                if tg_match:
                    socials['telegram'] = tg_match.group(1)
                else:
                    socials['telegram'] = href
            elif 'twitch.tv' in href.lower():
                socials['twitch'] = href

        skin_canvas = soup.find('canvas', class_=re.compile(r'skin-3d'))
        if skin_canvas:
            skin_id = skin_canvas.get('data-id')
            if skin_id:
                model = skin_canvas.get('data-model', 'slim')
                self.user_skins[username] = f"https://s.namemc.com/3d/skin/body.png?id={skin_id}&model={model}&width=100&height=100"

        if socials:
            self.user_socials[username] = socials
            if 'telegram' in socials:
                print(f"      [{username}] Telegram: @{socials['telegram']}")
            if 'steam' in socials:
                print(f"      [{username}] Steam найден")

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

        print("\nИзвлечение Telegram и Steam...")
        for html_file in html_files:
            name = html_file.stem
            if '_followers' not in name and '_following' not in name:
                username = name.split('.')[0]
                self.extract_socials_and_skin(html_file, username)

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
        print(f"   С Telegram/Steam: {len(self.user_socials)}")
        return True

    def save_telegram_steam_list(self, output_dir: Path):
        """Сохраняет список всех Telegram и Steam аккаунтов с привязкой к нику"""
        print(f"\nСохранение Telegram и Steam списка...")

        tg_file = output_dir / "telegram_users.txt"
        steam_file = output_dir / "steam_users.txt"
        tg_json = output_dir / "telegram_steam_full.json"

        tg_count = 0
        steam_count = 0

        with open(tg_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("TELEGRAM ПОЛЬЗОВАТЕЛЕЙ NameMC\n")
            f.write("="*60 + "\n")
            f.write(f"Всего: {sum(1 for s in self.user_socials.values() if 'telegram' in s)}\n")
            f.write("="*60 + "\n\n")
            f.write(f"{'N':<5} {'Nick NameMC':<35} {'Telegram':<35}\n")
            f.write("-"*80 + "\n")

            tg_list = []
            for user, socials in sorted(self.user_socials.items()):
                if 'telegram' in socials:
                    tg_count += 1
                    tg_username = socials['telegram']
                    tg_list.append({'nick': user, 'telegram': tg_username})
                    f.write(f"{tg_count:<5} {user:<35} @{tg_username:<35}\n")

            f.write("\n" + "="*60 + "\n")

        print(f"   готово: {tg_file.name} ({tg_count} Telegram аккаунтов)")

        with open(steam_file, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("STEAM ПОЛЬЗОВАТЕЛЕЙ NameMC\n")
            f.write("="*60 + "\n")
            f.write(f"Всего: {sum(1 for s in self.user_socials.values() if 'steam' in s)}\n")
            f.write("="*60 + "\n\n")
            f.write(f"{'N':<5} {'Nick NameMC':<35} {'Steam URL':<50}\n")
            f.write("-"*95 + "\n")

            steam_list = []
            for user, socials in sorted(self.user_socials.items()):
                if 'steam' in socials:
                    steam_count += 1
                    steam_url = socials['steam']
                    steam_list.append({'nick': user, 'steam': steam_url})
                    f.write(f"{steam_count:<5} {user:<35} {steam_url:<50}\n")

            f.write("\n" + "="*60 + "\n")

        print(f"   готово: {steam_file.name} ({steam_count} Steam аккаунтов)")

        full_data = {}
        for user, socials in self.user_socials.items():
            full_data[user] = {}
            if 'telegram' in socials:
                full_data[user]['telegram'] = socials['telegram']
            if 'steam' in socials:
                full_data[user]['steam'] = socials['steam']

        with open(tg_json, 'w', encoding='utf-8') as f:
            json.dump(full_data, f, indent=2, ensure_ascii=False)

        print(f"   готово: {tg_json.name} (полный JSON)")

        print(f"\nСтатистика Telegram/Steam:")
        print(f"   Telegram: {tg_count} пользователей")
        print(f"   Steam: {steam_count} пользователей")

        if tg_count > 0:
            print(f"\nПримеры Telegram:")
            tg_sample = [(u, s['telegram']) for u, s in sorted(self.user_socials.items()) if 'telegram' in s][:5]
            for user, tg in tg_sample:
                print(f"   {user} -> @{tg}")

        return tg_count, steam_count

    def generate_obsidian_notes(self, output_dir: Path):
        """Генерирует Obsidian заметки для всех пользователей"""
        print(f"\nГенерация Obsidian заметок для {len(self.all_users)} пользователей...")

        notes_dir = output_dir / "obsidian_notes"
        notes_dir.mkdir(exist_ok=True)

        social_icons = {
            'telegram': '[TG]',
            'steam': '[ST]',
            'github': '[GH]',
            'twitch': '[TW]'
        }

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
            f.write(f"- Всего связей: {len(self.all_edges)}\n")
            f.write(f"- Пользователей с соцсетями: {len(self.user_socials)}\n")
            f.write(f"- Telegram: {sum(1 for s in self.user_socials.values() if 'telegram' in s)}\n")
            f.write(f"- Steam: {sum(1 for s in self.user_socials.values() if 'steam' in s)}\n")
            f.write(f"- Discord полностью исключён\n\n")

            f.write("## Все пользователи\n\n")
            f.write("| Пользователь | Соцсети | Связей |\n")
            f.write("|-------------|---------|--------|\n")

            for user in sorted(self.all_users):
                social_str = ''
                if user in self.user_socials:
                    social_str = ' '.join([social_icons.get(p, p) for p in self.user_socials[user].keys()])
                connections = node_degree.get(user, 0)
                f.write(f"| [[{user}]] | {social_str} | {connections} |\n")

        print(f"   готово: {index_path.name}")

        user_count = 0
        for user in sorted(self.all_users):
            user_count += 1
            note_path = notes_dir / f"{user}.md"

            namemc_link = f"https://namemc.com/profile/{user}.1"
            avatar_link = self.user_skins.get(user, "")
            connections = node_degree.get(user, 0)

            with open(note_path, 'w', encoding='utf-8') as f:
                f.write("---\n")
                f.write(f"aliases: [{user}]\n")
                f.write(f"tags: [minecraft, player]\n")
                f.write(f"connections: {connections}\n")
                f.write(f"namemc: {namemc_link}\n")
                if user in self.user_socials:
                    for platform, link in self.user_socials[user].items():
                        f.write(f"{platform}: {link}\n")
                f.write("---\n\n")

                f.write(f"# {user}\n\n")
                f.write(f"[{user}]({namemc_link})\n\n")

                if avatar_link:
                    f.write(f"![]({avatar_link})\n\n")

                if user in self.user_socials:
                    f.write(f"## Соцсети\n\n")
                    for platform, link in self.user_socials[user].items():
                        icon = social_icons.get(platform, '[?]')
                        if platform == 'telegram':
                            f.write(f"- {icon} Telegram: @{link}\n")
                        else:
                            f.write(f"- {icon} {platform}: [{link}]({link})\n")
                    f.write("\n")

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

            f.write(f"{'N':<5} {'Пользователь':<35} {'Связей':<8} {'Telegram':<20} {'Steam':<20}\n")
            f.write("-" * 80 + "\n")

            for i, (user, degree) in enumerate(sorted_users, 1):
                tg = ''
                steam = ''
                if user in self.user_socials:
                    if 'telegram' in self.user_socials[user]:
                        tg = f"@{self.user_socials[user]['telegram']}"
                    if 'steam' in self.user_socials[user]:
                        steam = 'есть'
                f.write(f"{i:<5} {user:<35} {degree:<8} {tg:<20} {steam:<20}\n")

            f.write("\n" + "=" * 80 + "\n")
            f.write("Топ-10:\n")
            f.write("=" * 80 + "\n")
            for i, (user, degree) in enumerate(sorted_users[:10], 1):
                tg = ''
                if user in self.user_socials and 'telegram' in self.user_socials[user]:
                    tg = f" (@{self.user_socials[user]['telegram']})"
                f.write(f"{i:2}. {user} - {degree} связей{tg}\n")

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
        self.save_telegram_steam_list(output_dir)
        self.generate_obsidian_notes(output_dir)

        with open(output_dir / "all_users.txt", 'w', encoding='utf-8') as f:
            for user in sorted(self.all_users):
                f.write(f"{user}\n")

        print(f"\n   готово: all_users.txt (все {len(self.all_users)} пользователей)")

        print("\n" + "=" * 60)
        print("ГОТОВО!")
        print("=" * 60)
        print(f"\nИТОГИ:")
        print(f"   Пользователей: {len(self.all_users)}")
        print(f"   Связей: {len(self.all_edges)}")
        print(f"   Telegram: {sum(1 for s in self.user_socials.values() if 'telegram' in s)}")
        print(f"   Steam: {sum(1 for s in self.user_socials.values() if 'steam' in s)}")
        print(f"\nФАЙЛЫ в {output_dir}:")
        print(f"   top_users.txt - рейтинг с Telegram/Steam")
        print(f"   telegram_users.txt - все Telegram аккаунты")
        print(f"   steam_users.txt - все Steam аккаунты")
        print(f"   telegram_steam_full.json - полный JSON")
        print(f"   all_users.txt - список всех пользователей")
        print(f"   obsidian_notes/ - заметки Obsidian")
        print(f"\nDiscord полностью исключён")
        print("=" * 60)


def main():
    print("\n" + "=" * 60)
    print("АНАЛИЗАТОР ГРАФА NAMEMC (Telegram + Steam)")
    print("=" * 60)
    print("   Telegram - сохраняется в отдельный файл")
    print("   Steam - сохраняется в отдельный файл")
    print("   Привязка к нику NameMC")
    print("   Discord - полностью исключён")
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
