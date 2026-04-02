import asyncio
import json
import logging
import os
import random
from datetime import datetime

import aiofiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

BOT_TOKEN = "8666207577:AAHN0P84M6_BtaP-9fudB4ODaa1Z2nH4828"
ADMINS = [1033707280, 690328762, 1158607288, 568876466]

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TASKS_FILE = os.path.join(DATA_DIR, "user_tasks.json")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TASK_TEMPLATES = [
    {"id": 1,  "text": "Сфотографируйся с флагом Республики Башкортостан"},
    {"id": 2,  "text": "Сделай фото с лошадью"},
    {"id": 3,  "text": "Напиши пост о любви к мёду с хэштегом #курем и пришли ссылку"},
    {"id": 4,  "text": "Выучи стихотворение на башкирском языке и пришли видео"},
    {"id": 5,  "text": "Запиши видео под гимн Башкортостана"},
    {"id": 6,  "text": "Повтори позу памятника Салавату Юлаеву"},
    {"id": 7,  "text": "Приготовь кыстыбый и создай фотокарточку"},
    {"id": 8,  "text": "Подари эчпочмак организатору и пришли фото"},
    {"id": 9,  "text": "Возьми автограф у «чистого башкира»"},
    {"id": 10, "text": "Придумай героя Башкирии из членов Информа"},
    {"id": 11, "text": "Создай коллаж из башкирских орнаментов"},
    {"id": 12, "text": "Найди и сфотографируй национальный костюм"},
    {"id": 13, "text": "Расскажи легенду о Курае в сторис"},
    {"id": 14, "text": "Сфотографируй закат на фоне символики"},
    {"id": 15, "text": "Запиши видео с традиционным приветствием"},
]

TEXTS = {
    "start": "Привет! Это команда проекта «Курем» 👋\n\nКурем — национальный конкурс. Этот бот для геймификации и баллов!",
    "privacy": "Перед началом работы ознакомься с Политикой конфиденциальности (ред. 30.03.2026)...",
    "reg_name": "Введите ваше ФИО:",
    "reg_vk": "Введите ссылку на ваш профиль ВКонтакте:",
    "reg_institute": "Введите название вашего Института или Факультета:",
    "reg_success": "✅ Регистрация успешна!",
    "main_menu": "Выберите действие:",
    "task": "📋 Ваше задание:\n\n{task_text}",
    "task_sent": "✅ Задание отправлено на проверку!",
    "admin_menu": "🛡 Панель администратора:",
    "user_grade_notify": "🎉 Ура! Ты получил {grade} баллов за задание!",
    "user_rework_notify": "📝 Твое задание было отправлено на доработку.",
    "need_register": "Сначала зарегистрируйтесь через /start",
}

# ============================================================================
# FSM & DATABASE
# ============================================================================

class RegistrationForm(StatesGroup):
    name = State()
    vk = State()
    institute = State()

class TaskForm(StatesGroup):
    current_task_id = State()
    answer_type = State()
    answer_content = State()

class QuestionForm(StatesGroup):
    text = State()

class AdminAnswerForm(StatesGroup):
    question_id = State()
    waiting_answer = State()

async def _read_json(path: str) -> dict | list:
    if not os.path.exists(path):
        return [] if "tasks" in path or "questions" in path else {}
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
        if not content.strip(): return [] if "tasks" in path or "questions" in path else {}
        return json.loads(content)

async def _write_json(path: str, data: dict | list) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def _next_id(entity: str) -> int:
    counters = await _read_json(COUNTERS_FILE)
    if isinstance(counters, list): counters = {}
    counters[entity] = counters.get(entity, 0) + 1
    await _write_json(COUNTERS_FILE, counters)
    return counters[entity]

# --- Работа с пользователями и рейтингом ---
async def db_add_user(tg_id: int, name: str, vk: str, institute: str):
    users = await _read_json(USERS_FILE)
    users[str(tg_id)] = {"tg_id": tg_id, "name": name, "vk_link": vk, "institute": institute, "rating_score": 0, "created_at": datetime.now().isoformat()}
    await _write_json(USERS_FILE, users)

async def db_get_user(tg_id: int):
    users = await _read_json(USERS_FILE)
    return users.get(str(tg_id))

async def db_get_rating():
    users = await _read_json(USERS_FILE)
    if not users: return []
    # Сортировка по убыванию баллов
    return sorted(users.values(), key=lambda x: x.get("rating_score", 0), reverse=True)

# --- Работа с заданиями ---
async def db_create_user_task(user_id: int, template_id: int):
    tasks = await _read_json(TASKS_FILE)
    tid = await _next_id("user_tasks")
    tasks.append({"id": tid, "user_id": user_id, "template_id": template_id, "status": "viewing", "created_at": datetime.now().isoformat()})
    await _write_json(TASKS_FILE, tasks)
    return tid

async def db_update_task_answer(task_id: int, answer: str, answer_type: str):
    tasks = await _read_json(TASKS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            t.update({"user_answer": answer, "answer_type": answer_type, "status": "pending_review"})
            break
    await _write_json(TASKS_FILE, tasks)

async def db_get_pending_tasks():
    tasks = await _read_json(TASKS_FILE)
    users = await _read_json(USERS_FILE)
    res = []
    for t in tasks:
        if t.get("status") == "pending_review":
            u = users.get(str(t["user_id"]), {})
            tmpl = next((x for x in TASK_TEMPLATES if x["id"] == t["template_id"]), {"text": "—"})
            res.append({**t, "name": u.get("name", "Юзер"), "task_text": tmpl["text"]})
    return res

async def db_grade_task(task_id: int, grade: int):
    tasks = await _read_json(TASKS_FILE)
    user_id = None
    for t in tasks:
        if t["id"] == task_id:
            if t["status"] != "pending_review": return False
            t["admin_grade"] = grade
            t["status"] = "completed" if grade > 0 else "rework"
            user_id = t["user_id"]
            break
    if user_id:
        await _write_json(TASKS_FILE, tasks)
        if grade > 0:
            users = await _read_json(USERS_FILE)
            if str(user_id) in users:
                users[str(user_id)]["rating_score"] += grade
                await _write_json(USERS_FILE, users)
    return user_id

# --- Работа с вопросами ---
async def db_add_question(user_id: int, text: str):
    qs = await _read_json(QUESTIONS_FILE)
    qid = await _next_id("questions")
    qs.append({"id": qid, "user_id": user_id, "text": text, "status": "new", "created_at": datetime.now().isoformat()})
    await _write_json(QUESTIONS_FILE, qs)

async def db_get_new_questions():
    qs = await _read_json(QUESTIONS_FILE)
    users = await _read_json(USERS_FILE)
    res = []
    for q in qs:
        if q["status"] == "new":
            u = users.get(str(q["user_id"]), {})
            res.append({**q, "name": u.get("name", "—")})
    return res

async def db_answer_question(qid: int, text: str):
    qs = await _read_json(QUESTIONS_FILE)
    uid = None
    for q in qs:
        if q["id"] == qid:
            q["answer_text"], q["status"], uid = text, "answered", q["user_id"]
            break
    if uid: await _write_json(QUESTIONS_FILE, qs)
    return uid

# ============================================================================
# КЛАВИАТУРЫ
# ============================================================================

def get_privacy_kb():
    return InlineKeyboardBuilder().button(text="✅ Согласен", callback_data="privacy_agree").as_markup()

def get_main_menu_kb():
    b = ReplyKeyboardBuilder()
    b.button(text="📝 Выполнить задание")
    b.button(text="🏆 Рейтинг")
    b.button(text="❓ Задать вопрос организатору")
    b.adjust(1)
    return b.as_markup(resize_keyboard=True)

def get_task_action_kb():
    return InlineKeyboardBuilder().button(text="✅ Выполнить", callback_data="task_do").as_markup()

def get_answer_type_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Текст", callback_data="ans_text")
    kb.button(text="📎 Медиа", callback_data="ans_media")
    return kb.as_markup()

def get_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Задания", callback_data="adm_check_tasks")
    kb.button(text="💬 Вопросы", callback_data="adm_questions")
    kb.adjust(1)
    return kb.as_markup()

def get_grading_kb(task_id: int):
    kb = InlineKeyboardBuilder()
    for i in range(1, 6): kb.button(text=str(i), callback_data=f"grade_{task_id}_{i}")
    kb.button(text="🔄 Доработка", callback_data=f"grade_{task_id}_rework")
    kb.adjust(5)
    return kb.as_markup()

def get_question_list_kb(qs):
    kb = InlineKeyboardBuilder()
    for q in qs:
        kb.button(text=f"❓ От {q['name']}", callback_data=f"adm_q_{q['id']}")
    kb.adjust(1)
    return kb.as_markup()

# ============================================================================
# ХЕНДЛЕРЫ
# ============================================================================

class IsAdmin(BaseFilter):
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        return event.from_user.id in ADMINS

# --- Юзер часть ---
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS["start"])
    await message.answer(TEXTS["privacy"], reply_markup=get_privacy_kb())

async def privacy_agree(callback: types.CallbackQuery, state: FSMContext):
    if await db_get_user(callback.from_user.id):
        await callback.message.answer(TEXTS["main_menu"], reply_markup=get_main_menu_kb())
    else:
        await callback.message.edit_text(TEXTS["reg_name"])
        await state.set_state(RegistrationForm.name)

async def reg_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(TEXTS["reg_vk"])
    await state.set_state(RegistrationForm.vk)

async def reg_vk(message: types.Message, state: FSMContext):
    await state.update_data(vk=message.text)
    await message.answer(TEXTS["reg_institute"])
    await state.set_state(RegistrationForm.institute)

async def reg_institute(message: types.Message, state: FSMContext):
    data = await state.get_data()
    await db_add_user(message.from_user.id, data['name'], data['vk'], message.text)
    await state.clear()
    await message.answer(TEXTS["reg_success"], reply_markup=get_main_menu_kb())

async def do_task(message: types.Message, state: FSMContext):
    if not await db_get_user(message.from_user.id):
        await message.answer(TEXTS["need_register"])
        return
    tmpl = random.choice(TASK_TEMPLATES)
    tid = await db_create_user_task(message.from_user.id, tmpl["id"])
    await state.update_data(current_task_id=tid, task_text=tmpl["text"])
    await message.answer(TEXTS["task"].format(task_text=tmpl["text"]), reply_markup=get_task_action_kb())

async def task_do(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("Выберите формат ответа:", reply_markup=get_answer_type_kb())
    await state.set_state(TaskForm.answer_type)

async def answer_type_selected(callback: types.CallbackQuery, state: FSMContext):
    atype = callback.data.split("_")[1]
    await state.update_data(answer_type=atype)
    await callback.message.edit_text(f"Отправьте {'текст' if atype == 'text' else 'фото/видео/файл'}:")
    await state.set_state(TaskForm.answer_content)

async def receive_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    content = message.text or (message.photo[-1].file_id if message.photo else (message.video.file_id if message.video else message.document.file_id if message.document else None))
    if not content: return
    await db_update_task_answer(data["current_task_id"], content, "text" if message.text else "media")
    await state.clear()
    await message.answer(TEXTS["task_sent"])

# --- Рейтинг ---
async def show_rating(message: types.Message):
    rating = await db_get_rating()
    if not rating:
        await message.answer("Участников пока нет.")
        return
    text = "🏆 **Рейтинг участников «Курем»**\n\n"
    for i, u in enumerate(rating, 1):
        pref = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        text += f"{pref} **{u['name']}** — {u['rating_score']} б. ({u['institute']})\n"
    await message.answer(text, parse_mode="Markdown")

# --- Вопросы ---
async def ask_question_start(message: types.Message, state: FSMContext):
    await message.answer("Напишите ваш вопрос организатору:")
    await state.set_state(QuestionForm.text)

async def receive_question_text(message: types.Message, state: FSMContext):
    await db_add_question(message.from_user.id, message.text)
    await state.clear()
    await message.answer("✅ Вопрос отправлен! Ожидайте ответа.")

# --- Админка часть ---
async def cmd_admin(message: types.Message):
    await message.answer(TEXTS["admin_menu"], reply_markup=get_admin_kb())

async def adm_check_tasks(callback: types.CallbackQuery):
    tasks = await db_get_pending_tasks()
    if not tasks:
        await callback.answer("Заданий нет!", show_alert=True)
        return
    t = tasks[0]
    kb = get_grading_kb(t["id"])
    cap = f"📋 Задание #{t['id']}\n👤 {t['name']}\n📝 {t['task_text']}"
    if t["answer_type"] == "text":
        await callback.message.answer(f"{cap}\n\n💬 Ответ: {t['user_answer']}", reply_markup=kb)
    else:
        try: await callback.bot.send_photo(callback.from_user.id, photo=t["user_answer"], caption=cap, reply_markup=kb)
        except: await callback.bot.send_document(callback.from_user.id, document=t["user_answer"], caption=cap, reply_markup=kb)
    await callback.answer()

async def process_grade(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")
    task_id, val_str = int(parts[1]), parts[2]
    grade_val = 0 if val_str == "rework" else int(val_str)
    user_id = await db_grade_task(task_id, grade_val)
    
    if user_id is False:
        await callback.answer("Ошибка или уже проверено")
        return

    label = "Доработка" if grade_val == 0 else f"{grade_val} б."
    await callback.message.edit_text(f"✅ Оценено: {label}") if not callback.message.caption else await callback.message.edit_caption(caption=f"✅ Оценено: {label}")
    
    msg = TEXTS["user_rework_notify"] if grade_val == 0 else TEXTS["user_grade_notify"].format(grade=grade_val)
    try: await bot.send_message(user_id, msg)
    except: pass
    await callback.answer(f"Выставлено: {label}")

async def adm_questions(callback: types.CallbackQuery):
    qs = await db_get_new_questions()
    if not qs:
        await callback.answer("Новых вопросов нет", show_alert=True)
        return
    await callback.message.answer("Выберите вопрос:", reply_markup=get_question_list_kb(qs))
    await callback.answer()

async def adm_select_question(callback: types.CallbackQuery, state: FSMContext):
    qid = int(callback.data.split("_")[2])
    await state.update_data(question_id=qid)
    await callback.message.answer("Введите ответ:")
    await state.set_state(AdminAnswerForm.waiting_answer)
    await callback.answer()

async def admin_send_answer(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    uid = await db_answer_question(data["question_id"], message.text)
    if uid:
        try: await bot.send_message(uid, f"📬 **Ответ от организатора:**\n\n{message.text}", parse_mode="Markdown")
        except: pass
    await state.clear()
    await message.answer("✅ Ответ отправлен!")

# ============================================================================
# MAIN
# ============================================================================

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(privacy_agree, F.data == "privacy_agree")
    dp.message.register(reg_name, RegistrationForm.name)
    dp.message.register(reg_vk, RegistrationForm.vk)
    dp.message.register(reg_institute, RegistrationForm.institute)
    
    dp.message.register(do_task, F.text == "📝 Выполнить задание")
    dp.callback_query.register(task_do, F.data == "task_do")
    dp.callback_query.register(answer_type_selected, F.data.startswith("ans_"))
    dp.message.register(receive_answer, TaskForm.answer_content)
    
    dp.message.register(show_rating, F.text == "🏆 Рейтинг")
    dp.message.register(ask_question_start, F.text == "❓ Задать вопрос организатору")
    dp.message.register(receive_question_text, QuestionForm.text)
    
    dp.message.register(cmd_admin, Command("admin"), IsAdmin())
    dp.callback_query.register(adm_check_tasks, F.data == "adm_check_tasks", IsAdmin())
    dp.callback_query.register(process_grade, F.data.startswith("grade_"), IsAdmin())
    dp.callback_query.register(adm_questions, F.data == "adm_questions", IsAdmin())
    dp.callback_query.register(adm_select_question, F.data.startswith("adm_q_"), IsAdmin())
    dp.message.register(admin_send_answer, AdminAnswerForm.waiting_answer, IsAdmin())

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
