import asyncio
import re
from pathlib import Path
import pyperclip
from playwright.async_api import async_playwright

def clean_text(text):
    return re.sub(r'\s+', ' ', text.replace('\n', '').replace('\t', '')).strip()

def sanitize_card_name(name):
    return re.sub(r'[#<>\[\]{}|]', '', name)

def sanitize_deck_name(name):
    return re.sub(r'[<>:"/\\|?*]', '', name)

def ensure_english_url(url):
    if 'request_locale=' not in url:
        if '?' in url:
            url += '&request_locale=en'
        else:
            url += '?request_locale=en'
    else:
        url = re.sub(r'request_locale=\w+', 'request_locale=en', url)
    return url

def prompt_user_for_url():
    return input('> Enter Deck URL: ') 

def prompt_user_for_master_duel():
    while True:
        answer = input('> Is this a Master Duel Deck? (Y/N): ').strip().upper()
        if answer in ('Y', 'N'):
            return answer == 'Y'
        print('Invalid input. Please enter Y or N.')

def format_card_list(cards, is_master_duel):
    lines = []
    for card in cards:
        quantity = f' x{card["quantity"]}' if card["quantity"] > 1 else ''
        if is_master_duel:
            lines.append(f"* [[{card['name']} (Master Duel)|{card['name']}]]{quantity}")
        else:
            lines.append(f"* [[{card['name']}]]{quantity}")
    return '\n'.join(lines)

def count_total(cards):
    return sum(card['quantity'] for card in cards)

async def fetch_deck_data():
    print('\nLoading. Please wait...')
    decklists_dir = Path(__file__).parent / 'Decklists'
    if not decklists_dir.exists():
        decklists_dir.mkdir(exist_ok=True)
        print(f'Created directory: {decklists_dir}')

    async with async_playwright() as p:
        print('Please enter a valid Yu-Gi-Oh! Card Database Deck URL or type "exit" to quit.')
        browser = await p.chromium.launch(headless=True)
        try:
            while True:
                user_url = prompt_user_for_url()
                if user_url.lower() == 'exit':
                    break
                is_master_duel = prompt_user_for_master_duel()
                deck_url = ensure_english_url(user_url)
                print('Navigating to the entered page...')
                page = await browser.new_page()
                try:
                    await page.goto(deck_url, wait_until='networkidle')
                    print('  Waiting for the page elements to load...')
                    await page.wait_for_selector('.t_row.c_normal', state='attached', timeout=30000)

                    deck_name = await page.eval_on_selector('#broad_title h1', 'el => el.innerText.trim()')
                    if not deck_name:
                        deck_name = 'Unnamed Deck'
                    cleaned_deck_name = clean_text(deck_name)
                    sanitized_deck_name = sanitize_deck_name(cleaned_deck_name)
                    output_file = decklists_dir / f'{sanitized_deck_name} Decklist.txt'

                    print(f'  Processing Deck: {cleaned_deck_name}...')
                    deck_data = await page.evaluate(r'''() => {
                        function getMonsterType(typeText) {
                            if (typeText.includes('Ritual')) return 'ritual monsters';
                            if (typeText.includes('Pendulum')) return 'pendulum monsters';
                            if (typeText.includes('Tuner')) return 'tuner monsters';
                            if (typeText.includes('Gemini')) return 'gemini monsters';
                            if (typeText.includes('Union')) return 'union monsters';
                            if (typeText.includes('Spirit')) return 'spirit monsters';
                            if (typeText.includes('Toon')) return 'toon monsters';
                            if (typeText.includes('Effect')) return 'effect monsters';
                            return 'normal monsters';
                        }
                        function getExtraMonsterType(typeText) {
                            if (typeText.includes('Fusion')) return 'fusion monsters';
                            if (typeText.includes('Synchro')) return 'synchro monsters';
                            if (typeText.includes('Xyz')) return 'xyz monsters';
                            if (typeText.includes('Link')) return 'link monsters';
                            return 'fusion monsters';
                        }
                        const deck = {
                            main: { monsters: [], spells: [], traps: [] },
                            extra: { monsters: [] },
                            side: { monsters: [], spells: [], traps: [] }
                        };
                        function sanitizeCardName(name) {
                            return name.replace(/[#<>\[\]{}|]/g, '');
                        }
                        function processCard(card, section) {
                            const name = sanitizeCardName(card.querySelector('.card_name')?.innerText.trim() || 'Name not found');
                            const quantity = parseInt(card.querySelector('.cards_num_set span')?.innerText.trim()) || 1;
                            const attributeElement = card.querySelector('.box_card_attribute span');
                            const attribute = attributeElement ? attributeElement.innerText.trim() : '';
                            if (attribute === 'SPELL' || attribute === 'TRAP') {
                                if (section === 'main') {
                                    if (attribute === 'SPELL') deck.main.spells.push({ name, quantity });
                                    else if (attribute === 'TRAP') deck.main.traps.push({ name, quantity });
                                } else if (section === 'side') {
                                    if (attribute === 'SPELL') deck.side.spells.push({ name, quantity });
                                    else if (attribute === 'TRAP') deck.side.traps.push({ name, quantity });
                                }
                            } else {
                                const typeText = card.querySelector('.card_info_species_and_other_item')?.innerText.trim() || '';
                                if (section === 'main') {
                                    const type = getMonsterType(typeText);
                                    deck.main.monsters.push({ name, quantity, type });
                                } else if (section === 'extra') {
                                    const type = getExtraMonsterType(typeText);
                                    deck.extra.monsters.push({ name, quantity, type });
                                } else if (section === 'side') {
                                    const type = getMonsterType(typeText);
                                    deck.side.monsters.push({ name, quantity, type });
                                }
                            }
                        }
                        document.querySelectorAll('#detailtext_main .t_row.c_normal').forEach(card => processCard(card, 'main'));
                        document.querySelectorAll('#detailtext_ext .t_row.c_normal').forEach(card => processCard(card, 'extra'));
                        document.querySelectorAll('#detailtext_side .t_row.c_normal').forEach(card => processCard(card, 'side'));
                        return deck;
                    }''')

                    main_monsters = {
                        'normal monsters': [],
                        'effect monsters': [],
                        'toon monsters': [],
                        'spirit monsters': [],
                        'union monsters': [],
                        'gemini monsters': [],
                        'tuner monsters': [],
                        'pendulum monsters': [],
                        'ritual monsters': []
                    }
                    for monster in deck_data['main']['monsters']:
                        main_monsters[monster['type']].append({'name': monster['name'], 'quantity': monster['quantity']})
                    extra_monsters = {
                        'fusion monsters': [],
                        'synchro monsters': [],
                        'xyz monsters': [],
                        'link monsters': []
                    }
                    for monster in deck_data['extra']['monsters']:
                        extra_monsters[monster['type']].append({'name': monster['name'], 'quantity': monster['quantity']})
                    side_monsters = {
                        'side normal monsters': [],
                        'side effect monsters': [],
                        'side toon monsters': [],
                        'side spirit monsters': [],
                        'side union monsters': [],
                        'side gemini monsters': [],
                        'side tuner monsters': [],
                        'side pendulum monsters': [],
                        'side ritual monsters': []
                    }
                    for monster in deck_data['side']['monsters']:
                        side_monsters[f'side {monster["type"]}'].append({'name': monster['name'], 'quantity': monster['quantity']})
                    total_monsters = count_total(deck_data['main']['monsters'])
                    total_extra_monsters = count_total(deck_data['extra']['monsters'])
                    total_spells = count_total(deck_data['main']['spells'])
                    total_traps = count_total(deck_data['main']['traps'])
                    template = (
                        f"{{{{Decklist|{cleaned_deck_name}\n"
                        f"<!-- Main Deck -->\n"
                        f"| total m = {total_monsters}\n"
                    )
                    template += '\n'.join([
                        f'| {type_} =\n{format_card_list(cards, is_master_duel)}'
                        for type_, cards in main_monsters.items() if cards
                    ])
                    template += f"\n| total s = {total_spells}\n"
                    if deck_data['main']['spells']:
                        template += f"| spells =\n{format_card_list(deck_data['main']['spells'], is_master_duel)}\n"
                    template += f"| total t = {total_traps}\n"
                    if deck_data['main']['traps']:
                        template += f"| traps =\n{format_card_list(deck_data['main']['traps'], is_master_duel)}\n"
                    template += f"\n<!-- Extra Deck -->\n| total me = {total_extra_monsters}\n"
                    template += '\n'.join([
                        f'| {type_} =\n{format_card_list(cards, is_master_duel)}'
                        for type_, cards in extra_monsters.items() if cards
                    ])
                    template += '\n'
                    template += '\n<!-- Side Deck -->\n'
                    template += '\n'.join([
                        f'| {type_} =\n{format_card_list(cards, is_master_duel)}'
                        for type_, cards in side_monsters.items() if cards
                    ])
                    if deck_data['side']['spells']:
                        template += f"| side spells =\n{format_card_list(deck_data['side']['spells'], is_master_duel)}"
                    if deck_data['side']['traps']:
                        template += f"| side traps =\n{format_card_list(deck_data['side']['traps'], is_master_duel)}"
                    template += '\n}}'
                    print(f'  Saving the Decklist to the file: {output_file}...')
                    try:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(template.strip())
                        print('\033[92mFile saved successfully!\033[0m')
                    except Exception as e:
                        print(f'\033[91mError saving file: {e}\033[0m')
                    finally:
                        try:
                            pyperclip.copy(template.strip())
                            print('\033[92mDecklist copied to clipboard!\033[0m')
                        except Exception as e:
                            print(f'\033[91mCould not copy to clipboard: {e}\033[0m')
                except Exception as e:
                    print(f'\033[91mERROR: {e}\033[0m')
                finally:
                    await page.close()
        except Exception as e:
            print(f'\033[91mError extracting data: {e}\033[0m')
        finally:
            print('Ending...')
            await browser.close()

if __name__ == '__main__': 
    asyncio.run(fetch_deck_data())