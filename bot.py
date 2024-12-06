import asyncio
import logging
import sys
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import db
from settings import settings


API_TOKEN = settings.API_TOKEN
logging.basicConfig(level=logging.INFO)

form_router = Router()


class Form(StatesGroup):
    user_id = State()
    first_name = State()
    phone = State()
    role = State()
    bonuses = State()
    time_bonuses = State()


@form_router.message(F.text.regexp(r"Админ: \d{11}"))
async def set_admin(message: Message):
    admin = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] != "super_admin":
        await message.answer("У вас недостаточно прав!")
        return
    phone = message.text.split(" ")[-1]
    await db[settings.DB_COLLECTION].update_one(
        {"phone": phone}, {"$set": {"role": "admin"}}
    )
    await message.answer("Админ добавлен.")


@form_router.message(F.text.regexp(r"Пользователь: \d{11}"))
async def remove_admin(message: Message):
    admin = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] != "super_admin":
        await message.answer("У вас недостаточно прав!")
        return
    phone = message.text.split(" ")[-1]
    await db[settings.DB_COLLECTION].update_one(
        {"phone": phone}, {"$set": {"role": "user"}}
    )
    await message.answer("Админ удалён.")


async def find_user(user_id):
    result = await db[settings.DB_COLLECTION].find_one({"user_id": user_id})
    return result


async def insert_user(user_data):
    instance = await db[settings.DB_COLLECTION].insert_one(user_data)
    return await db[settings.DB_COLLECTION].find_one(
        {"_id": instance.inserted_id}
    )


async def check_and_reset_bonus(user_id, message):
    user = await db[settings.DB_COLLECTION].find_one({"user_id": user_id})
    last_bonus_date = datetime.strptime(user["time_bonuses"], "%d:%m:%Y")
    current_date = datetime.now()
    delta = timedelta(days=60)

    if current_date - last_bonus_date >= delta:
        await db[settings.DB_COLLECTION].update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "bonuses": 0,
                    "time_bonuses": current_date.strftime("%d:%m:%Y"),
                }
            },
        )
        return await message.answer(
            "Бонусы сгорели по истечению двух месяцев."
        )


@form_router.message(CommandStart())
async def command_start(message: Message) -> None:
    user = await find_user(user_id=message.from_user.id)

    if user is not None and user["role"] in ["super_admin", "admin"]:
        await message.answer(
            "Введите номер телефона клиента в формате\n 'Клиент: номер_телефона'"
        )
        return

    if user is None:
        user_data = {
            "user_id": message.from_user.id,
            "first_name": message.from_user.first_name,
            "role": "user",
            "bonuses": 0,
            "time_bonuses": datetime.now().date().strftime("%d:%m:%Y"),
        }
        user = await insert_user(user_data=user_data)

    kb = [[types.KeyboardButton(text="Показать мои бонусы")]]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    await message.answer(
        "Приветствую! Я чатбот автомойки BlackWater!",
        reply_markup=keyboard,
    )

    if user.get("phone") is None:
        await message.answer("Введите номер телефона в формате 8ХХХХХХХХХХ:")


@form_router.message(F.text.regexp(r"\d{11}"))
async def add_phone_number(message: Message) -> None:
    user = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    await db[settings.DB_COLLECTION].update_one(
        {"_id": user["_id"]}, {"$set": {"phone": message.text}}
    )
    await message.answer(f"Ваш бонусный счёт: {user['bonuses']}")


@form_router.message(F.text == "Показать мои бонусы")
async def info_user_bonuses(message: Message) -> None:
    await check_and_reset_bonus(message.from_user.id, message)
    user = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    await message.answer(f"Ваш бонусный счёт: {user['bonuses']}")


@form_router.message(F.text.regexp(r"Клиент: \d{11}"))
async def find_phone_user(message: Message, state: FSMContext) -> None:
    admin = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] not in ["super_admin", "admin"]:
        await message.answer("Вы не являетесь админестратором!")
        return
    client = await db[settings.DB_COLLECTION].find_one(
        {"phone": message.text.split(" ")[-1]}
    )
    if client is None:
        await message.answer(
            "Такого номера телефона нет в базе либо вы ввели некорректно"
        )
        await message.answer(
            "Введите номер телефона клиента в формате\n 'Клиент: номер_телефона'"
        )
        return
    client.pop("_id")
    await state.update_data(**client)

    await message.answer(f"Бонусный счёт: {client['bonuses']}")
    await message.answer(
        "Выбери и запиши команду: \n 'Списать: число_бонусов' или 'Начислить: сумма_покупки'"
    )


@form_router.message(F.text.regexp(r"Списать: \d+"))
async def bonus_debit(message: Message, state: FSMContext) -> None:
    admin = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] not in ["super_admin", "admin"]:
        await message.answer("Вы не являетесь админестратором!")
        return

    client = await state.get_data()
    await check_and_reset_bonus(client["user_id"], message)

    user = await db[settings.DB_COLLECTION].find_one(
        {"user_id": client["user_id"]}
    )
    user.pop("_id")
    await state.update_data(**user)
    client = await state.get_data()
    value = message.text.split(" ")[-1]

    if client["bonuses"] < int(value):
        await message.answer("Недостаточно бонусов.")
        return
    client["bonuses"] -= int(value)

    await state.update_data(bonuses=client["bonuses"])
    await db[settings.DB_COLLECTION].update_one(
        {"user_id": client["user_id"]},
        {"$set": {"bonuses": client["bonuses"]}},
    )
    await message.answer(
        f"Бонусы списаны!\n Текущий баланс: {client['bonuses']} бонусов."
    )


@form_router.message(F.text.regexp(r"Начислить: \d+"))
async def bonus_credit(message: Message, state: FSMContext) -> None:
    user = await db[settings.DB_COLLECTION].find_one(
        {"user_id": message.from_user.id}
    )
    if user["role"] not in ["super_admin", "admin"]:
        await message.answer("Вы не являетесь админестратором!")
        return

    client = await state.get_data()
    value = int(message.text.split(" ")[-1])
    value = value * 0.05
    client["bonuses"] += int(value)

    await state.update_data(bonuses=client["bonuses"])
    await db[settings.DB_COLLECTION].update_one(
        {"user_id": client["user_id"]},
        {"$set": {"bonuses": client["bonuses"]}},
    )
    await message.answer(
        f"Бонусы зачислены!\n Текущий баланс: {client['bonuses']} бонусов."
    )


async def main():

    bot = Bot(
        token=API_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
