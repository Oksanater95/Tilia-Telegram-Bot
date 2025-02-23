from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import (
    orm_change_banner_image,
    orm_get_categories,
    orm_add_product,
    orm_delete_product,
    orm_get_info_pages,
    orm_get_product,
    orm_get_products,
    orm_update_product,
)

from filters.chat_types import ChatTypeFilter, IsAdmin

from kbds.inline import get_callback_btns
from kbds.reply import get_keyboard


admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())


ADMIN_KB = get_keyboard(
    "Produkt hinzufügen",
    "Sortiment",
    "Banner hinzufügen/ändern",
    placeholder="Wählen Sie eine Aktion",
    sizes=(2,),
)



@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Was möchten Sie tun?", reply_markup=ADMIN_KB)


@admin_router.message(F.text == 'Sortiment')
async def admin_features(message: types.Message, session: AsyncSession):
    categories = await orm_get_categories(session)
    btns = {category.name : f'category_{category.id}' for category in categories}
    await message.answer("Wählen Sie eine Kategorie", reply_markup=get_callback_btns(btns=btns))


@admin_router.callback_query(F.data.startswith('category_'))
async def starring_at_product(callback: types.CallbackQuery, session: AsyncSession):
    category_id = callback.data.split('_')[-1]
    for product in await orm_get_products(session, int(category_id)):
        await callback.message.answer_photo(
            product.image,
            caption=f"<strong>{product.name}\
                    </strong>\n{product.description}\nPreis: {round(product.price, 2)}",
            reply_markup=get_callback_btns(
                btns={
                    "Löschen": f"delete_{product.id}",
                    "Ändern": f"change_{product.id}",
                },
                sizes=(2,)
            ),
        )
    await callback.answer()
    await callback.message.answer("OK, hier ist die Produktliste ⏫ ⏫")


@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(callback: types.CallbackQuery, session: AsyncSession):
    product_id = callback.data.split("_")[-1]
    await orm_delete_product(session, int(product_id))

    await callback.answer("Produkt gelöscht")
    await callback.message.answer("Produkt gelöscht!")


################# Mikro-FSM zum Hochladen/Ändern von Bannern ############################

class AddBanner(StatesGroup):
    image = State()

# Wir senden die Liste der Informationsseiten des Bots und wechseln in den Zustand zum Senden des Fotos
@admin_router.message(StateFilter(None), F.text == 'Banner hinzufügen/ändern')
async def add_image2(message: types.Message, state: FSMContext, session: AsyncSession):
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    await message.answer(f"Senden Sie das Bannerfoto..\nGeben Sie in der Beschreibung an, für welche Seite es ist:\
                         \n{', '.join(pages_names)}")
    await state.set_state(AddBanner.image)

# # Wir fügen ein Bild hinzu/ändern es in der Tabelle (es gibt bereits gespeicherte Seiten mit den Namen:
# main, catalog, cart (für leeren Warenkorb), about, payment, shipping)
@admin_router.message(AddBanner.image, F.photo)
async def add_banner(message: types.Message, state: FSMContext, session: AsyncSession):
    image_id = message.photo[-1].file_id
    for_page = message.caption.strip()
    pages_names = [page.name for page in await orm_get_info_pages(session)]
    if for_page not in pages_names:
        await message.answer(f"Geben Sie einen gültigen Seitennamen ein, zum Beispiel:\
                         \n{', '.join(pages_names)}")
        return
    await orm_change_banner_image(session, for_page, image_id,)
    await message.answer("Banner hinzugefügt/geändert.")
    await state.clear()

# Wir fangen fehlerhafte Eingaben ab
@admin_router.message(AddBanner.image)
async def add_banner2(message: types.Message, state: FSMContext):
    await message.answer("enden Sie ein Bannerfoto oder brechen Sie ab")

#########################################################################################


#########################################################################################



######################### FSM für das Hinzufügen/Ändern von Produkten ###################

class AddProduct(StatesGroup):
    
    name = State()
    description = State()
    category = State()
    price = State()
    image = State()

    product_for_change = None

    texts = {
        "AddProduct:name": "Geben Sie den Namen erneut ein:",
        "AddProduct:description": "Geben Sie die Beschreibung erneut ein:",
        "AddProduct:category": "Wählen Sie die Kategorie erneut ⬆️",
        "AddProduct:price": "Geben Sie den Preis erneut ein:",
        "AddProduct:image": "Dies ist der letzte Schritt...",
    }


# Wechseln in den Zustand zum Eingeben des Namens
@admin_router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_product_callback(
    callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    product_id = callback.data.split("_")[-1]

    product_for_change = await orm_get_product(session, int(product_id))

    AddProduct.product_for_change = product_for_change

    await callback.answer()
    await callback.message.answer(
        "Geben Sie den Produktnamen ein", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


# Становимся в состояние ожидания ввода name
@admin_router.message(StateFilter(None), F.text == "Produkt hinzufügen")
async def add_product(message: types.Message, state: FSMContext):
    await message.answer(
        "Geben Sie den Produktnamen ein", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


# Abbruch-Handler nach dem ersten Zustand
# после того, как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter("*"), Command("abbrechen"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "abbrechen")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddProduct.product_for_change:
        AddProduct.product_for_change = None
    await state.clear()
    await message.answer("Aktionen wurden abgebrochen", reply_markup=ADMIN_KB)


# Schritt zurückgehen
@admin_router.message(StateFilter("*"), Command("zurück"))
@admin_router.message(StateFilter("*"), F.text.casefold() == "zurück")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddProduct.name:
        await message.answer(
            'Kein vorheriger Schritt. Geben Sie den Namen ein oder schreiben Sie "abbrechen"'
        )
        return

    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(
                f"Ok, sie sind zurück zum vorherigen Schritt \n {AddProduct.texts[previous.state]}"
            )
            return
        previous = step


# Erfassen der Daten für den Zustand name und dann Wechsel zum Zustand description
@admin_router.message(AddProduct.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        # Hier kann eine zusätzliche Überprüfung durchgeführt werden
        # und der Handler verlassen werden, ohne den Zustand zu ändern,
        # mit dem Senden einer entsprechenden Nachricht.
        # Zum Beispiel:
        if 4 >= len(message.text) >= 150:
            await message.answer(
                "Der Produktname darf nicht länger als 150 Zeichen sein\noder weniger als 5 Zeichen haben. \n Bitte erneut eingeben"
            )
            return

        await state.update_data(name=message.text)
    await message.answer("Geben Sie die Produktbeschreibung ein")
    await state.set_state(AddProduct.description)

# Handler zum Abfangen ungültiger Eingaben für den Zustand name
@admin_router.message(AddProduct.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer("Ungültige Daten eingegeben, bitte geben Sie den Produktnamen als Text ein")


# Erfassen der Daten für den Zustand description und dann Wechsel zum Zustand price
@admin_router.message(AddProduct.description, F.text)
async def add_description(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(description=AddProduct.product_for_change.description)
    else:
        if 4 >= len(message.text):
            await message.answer(
                "Die Beschreibung ist zu kurz. \n Bitte erneut eingeben."
            )
            return
        await state.update_data(description=message.text)

    categories = await orm_get_categories(session)
    btns = {category.name : str(category.id) for category in categories}
    await message.answer("Wählen Sie eine Kategorie aus", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddProduct.category)

# Handler zum Abfangen ungültiger Eingaben für den Zustand description
@admin_router.message(AddProduct.description)
async def add_description2(message: types.Message, state: FSMContext):
    await message.answer("Ungültige Daten eingegeben, bitte geben Sie die Produktbeschreibung als Text ein")


# Erfassen des Callback für die Kategorieauswahl
@admin_router.callback_query(AddProduct.category)
async def category_choice(callback: types.CallbackQuery, state: FSMContext , session: AsyncSession):
    if int(callback.data) in [category.id for category in await orm_get_categories(session)]:
        await callback.answer()
        await state.update_data(category=callback.data)
        await callback.message.answer('Geben Sie nun den Produktpreis ein.')
        await state.set_state(AddProduct.price)
    else:
        await callback.message.answer('Wählen Sie eine Kategorie über die Buttons aus.')
        await callback.answer()

# Abfangen aller ungültigen Aktionen außer dem Drücken des Kategorie-Auswahl-Buttons
@admin_router.message(AddProduct.category)
async def category_choice2(message: types.Message, state: FSMContext):
    await message.answer("'Wählen Sie eine Kategorie über die Buttons aus.")


# Erfassen der Daten für den Zustand price und dann Wechsel zum Zustand image
@admin_router.message(AddProduct.price, F.text)
async def add_price(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(price=AddProduct.product_for_change.price)
    else:
        try:
            float(message.text)
        except ValueError:
            await message.answer("Geben Sie einen gültigen Preis ein")
            return

        await state.update_data(price=message.text)
    await message.answer("Laden Sie ein Produktbild hoch")
    await state.set_state(AddProduct.image)

# Handler zum Abfangen ungültiger Eingaben für den Zustand price
@admin_router.message(AddProduct.price)
async def add_price2(message: types.Message, state: FSMContext):
    await message.answer("Ungültige Eingabe. Bitte geben Sie den Produktpreis ein")


# Erfassen der Daten für den Zustand image und anschließend Beendigung des Zustands
@admin_router.message(AddProduct.image, or_f(F.photo, F.text == "."))
async def add_image(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text and message.text == "." and AddProduct.product_for_change:
        await state.update_data(image=AddProduct.product_for_change.image)

    elif message.photo:
        await state.update_data(image=message.photo[-1].file_id)
    else:
        await message.answer("Bitte senden Sie ein Bild des Gerichts.")
        return
    data = await state.get_data()
    try:
        if AddProduct.product_for_change:
            await orm_update_product(session, AddProduct.product_for_change.id, data)
        else:
            await orm_add_product(session, data)
        await message.answer("Produkt hinzugefügt/geändert", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Fehler \n{str(e)}\nBitte wenden Sie sich an den Programmierer – er will wahrscheinlich wieder Geld",
            reply_markup=ADMIN_KB,
        )
        await state.clear()

    AddProduct.product_for_change = None

# Abfangen aller sonstigen ungültigen Eingaben für den Zustand image
@admin_router.message(AddProduct.image)
async def add_image2(message: types.Message, state: FSMContext):
    await message.answer("Bitte senden Sie ein Bild des Gerichts")