import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from dotenv import load_dotenv

from database import db


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
logging.basicConfig(level=logging.INFO)

form_router = Router()


class Form(StatesGroup):
    user_id = State()
    first_name = State()
    phone = State()
    role = State()
    bonuses = State()


@form_router.message(F.text.regexp(r"Админ: \d{11}"))
async def set_admin(message: Message):
    admin = await db.test_collection.find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] != "admin":
        await message.answer("Вы не являетесь админестратором!")
        return
    phone = message.text.split(" ")[-1]
    await db.test_collection.update_one(
        {"phone": phone}, {"$set": {"role": "admin"}}
    )


async def find_user(user_id):
    result = await db.test_collection.find_one({"user_id": user_id})
    return result


async def insert_user(user_data):
    instance = await db.test_collection.insert_one(user_data)
    return await db.test_collection.find_one({"_id": instance.inserted_id})


@form_router.message(CommandStart())
async def command_start(message: Message) -> None:
    user = await find_user(user_id=message.from_user.id)

    if user is not None and user["role"] == "admin":
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
        }
        user = await insert_user(user_data=user_data)

    await message.answer(
        "Приветствую! Я чатбот автомойки BlackWater!",
        reply_markup=ReplyKeyboardRemove(),
    )
    if user.get("phone") is None:
        await message.answer("Введите номер телефона:")


@form_router.message(F.text.regexp(r"\d{11}"))
async def add_phone_number(message: Message) -> None:
    user = await db.test_collection.find_one({"user_id": message.from_user.id})
    await db.test_collection.update_one(
        {"_id": user["_id"]}, {"$set": {"phone": message.text}}
    )
    await message.answer(f"Ваш бонусный счёт: {user['bonuses']}")


@form_router.message(F.text.regexp(r"Клиент: \d{11}"))
async def find_phone_user(message: Message, state: FSMContext) -> None:
    admin = await db.test_collection.find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] != "admin":
        await message.answer("Вы не являетесь админестратором!")
        return
    client = await db.test_collection.find_one(
        {"phone": message.text.split(" ")[-1]}
    )
    client.pop("_id")
    await state.update_data(**client)

    await message.answer(f"Бонусный счёт: {client['bonuses']}")
    await message.answer(
        "Выбери и запиши команду: \n 'Списать: число_бонусов' или 'Начислить: сумма_покупки'"
    )


@form_router.message(F.text.regexp(r"Списать: \d+"))
async def bonus_debit(message: Message, state: FSMContext) -> None:
    admin = await db.test_collection.find_one(
        {"user_id": message.from_user.id}
    )
    if admin["role"] != "admin":
        await message.answer("Вы не являетесь админестратором!")
        return
    client = await state.get_data()
    value = message.text.split(" ")[-1]

    if client["bonuses"] < value:
        await message.answer("Недостаточно бонусов.")
        return
    client["bonuses"] -= int(value)

    await state.update_data(bonuses=client["bonuses"])
    await db.test_collection.update_one(
        {"user_id": client["user_id"]},
        {"$set": {"bonuses": client["bonuses"]}},
    )
    await message.answer(
        f"Бонусы списаны!\n Текущий баланс: {client['bonuses']} бонусов."
    )


@form_router.message(F.text.regexp(r"Начислить: \d+"))
async def bonus_credit(message: Message, state: FSMContext) -> None:
    user = await db.test_collection.find_one({"user_id": message.from_user.id})
    if user["role"] != "admin":
        await message.answer("Вы не являетесь админестратором!")
        return

    client = await state.get_data()
    value = int(message.text.split(" ")[-1])
    value = value * 0.05
    client["bonuses"] += int(value)

    await state.update_data(bonuses=client["bonuses"])
    await db.test_collection.update_one(
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
