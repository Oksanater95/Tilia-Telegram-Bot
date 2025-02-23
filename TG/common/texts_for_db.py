from aiogram.utils.formatting import Bold, as_list, as_marked_section

# Kategorien
categories = ['Essen', 'Getränke']

# Beschreibungen für Info-Seiten
description_for_info_pages = {
    "main": "Willkommen!",
    "about": "🍽️ Tilia Restaurant & Bar.\n🕰️ Öffnungszeiten: Täglich von 10:00 bis 22:00 Uhr. \nWillkommen bei Tilia Restaurant & Bar! ✨\nGenießen Sie unsere köstlichen Speisen und erfrischenden Getränke direkt vor Ort 🪑 oder bestellen Sie bequem von überall aus 🛵📱.\n🍕 Frisch.\n🥗 Lecker.\n🍹 Für jeden Geschmack etwas dabei!\n📲 Bestellen leicht gemacht: Nutzen Sie unseren praktischen Telegram-Bot 🤖, um schnell und einfach Ihr Lieblingsgericht auszuwählen.\nWir freuen uns auf Sie! 💚",
    "payment": as_marked_section(
        Bold("Zahlungsmöglichkeiten:"),
        "Mit Karte im Bot",
        "Bei Erhalt mit Karte/Bar",
        "Im Restaurant",
        marker="✅ ",
    ).as_html(),
    "shipping": as_list(
        as_marked_section(
            Bold("Liefer-/Bestellmöglichkeiten:"),
            "Kurrier",
            "Selbstabholung (komme gleich vorbei und hole es ab)",
            "Vor Ort essen (komme gleich vorbei)",
            marker="✅ ",
        ),
        as_marked_section(Bold("Nicht möglich:"), "Post", "Brieftauben", marker="❌ "),
        sep="\n----------------------\n",
    ).as_html(),
    'catalog': 'Kategorien:',
    'cart': 'Der Warenkorb ist leer!'
}