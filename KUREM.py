# ============================================================================
# КУРЕМ БОТ — Телеграм бот для проекта КУРЕМ
# Технологии: Python 3.10+, aiogram 3.x, JSON-файлы (без SQL)
# ============================================================================

import asyncio
import json
import logging
import os
import random
from datetime import datetime

import aiofiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter, BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

BOT_TOKEN = "8666207577:AAHN0P84M6_BtaP-9fudB4ODaa1Z2nH4828"
ADMINS = [1033707280, 690328762, 1158607288, 568876466]

# Пути к JSON-файлам хранилища
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
TASKS_FILE = os.path.join(DATA_DIR, "user_tasks.json")
QUESTIONS_FILE = os.path.join(DATA_DIR, "questions.json")
COUNTERS_FILE = os.path.join(DATA_DIR, "counters.json")

if not BOT_TOKEN or BOT_TOKEN == "ВАШ_ТОКЕН_ОТ_BOTFATHER":
    raise ValueError("Пожалуйста, вставьте valid BOT_TOKEN в конфигурацию!")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# ШАБЛОНЫ ЗАДАНИЙ
# ============================================================================

TASK_TEMPLATES = [
    {"id": 1,  "text": "Сфотографируйся с флагом Республики Башкортостан"},
    {"id": 2,  "text": "Сделай фото с лошадью"},
    {"id": 3,  "text": "Напиши пост о любви к мёду с хэштегом #курем и размести его на своей странице ВК и пришли ссылку"},
    {"id": 4,  "text": "Выучи стихотворение на башкирском языке и пришли видео, как рассказываешь его"},
    {"id": 5,  "text": "Запиши видео под гимн Башкортостана"},
    {"id": 6,  "text": "Повтори позу памятника Салавату Юлаеву"},
    {"id": 7,  "text": "Приготовь кыстыбый и создай фотокарточку"},
    {"id": 8,  "text": "Подари эчпочмак организатору и пришли фото"},
    {"id": 9,  "text": "Возьми автограф у «чистого башкира»"},
    {"id": 10, "text": "Придумай, кто из членов Информа был бы каким героем Башкирии и пришли текст"},
    {"id": 11, "text": "Создай коллаж из башкирских орнаментов"},
    {"id": 12, "text": "Найди и сфотографируй национальный костюм"},
    {"id": 13, "text": "Расскажи легенду о Курае в формате сторис"},
    {"id": 14, "text": "Сфотографируй закат на фоне национальной символики"},
    {"id": 15, "text": "Запиши видео с традиционным приветствием"},
]

# ============================================================================
# ТЕКСТЫ
# ============================================================================

TEXTS = {
    "start": (
        "Привет! Это команда проекта «Курем» 👋\n\n"
        "Курем — национальный конкурс для разных направлений ИК "
        "(фото, видео, дизайн, смм). Основная тематика — башкирские традиции "
        "в современных реалиях.\n\n"
        "Этот бот создан для геймификации конкурса: здесь будут публиковаться "
        "дополнительные задания, за выполнение которых ты сможешь получить "
        "дополнительные баллы. "
        "Следи за обновлениями и не упускай возможность повысить свой итоговый результат!"
    ),
    "privacy": (
        "Перед началом работы ознакомься с Политикой конфиденциальности редакция от 30.03.2026 (далее – Политика) нашего бота!\n\n"
        "Используя Бота и нажимая кнопку «✅ Согласен», ты подтверждаешь, что:\n"
        "• Ознакомился с настоящей Политикой;\n"
        "• Понимаешь условия обработки твоих данных;\n"
        "• Даёшь добровольное согласие на их обработку.\n\n"
        "🔹 Мы собираем следующие данные:\n"
        "• ФИО;\n"
        "• Ссылка на профиль ВКонтакте;\n"
        "• Институт или Факультет.\n\n"
        "🔹 Данные необходимы для:\n"
        "• Регистрации;\n"
        "• Выдачи персональных заданий;\n"
        "• Проверки и начисления баллов;\n"
        "• Формирования рейтинга участника.\n\n"
        "🔹 Мы НЕ используем твои данные для:\n"
        "• Передачи третьим лицам;\n"
        "• Коммерческой рекламы и спама.\n\n"
        "🔹 Доступ к данным имеют только:\n"
        "• Организаторы проекта — Ариадна Хаванова и Азалия Галиуллина;\n"
        "• Разработчик — Чеченков Никита.\n\n"
        "Организаторы вправе обновлять Политику. Участники будут проинформированы через Бота."
    ),
    "access_denied":    "Доступ заблокирован. Вы не приняли условия.",
    "reg_name":         "Введите ваше ФИО:",
    "reg_vk":           "Введите ссылку на ваш профиль ВКонтакте:",
    "reg_institute":    "Введите название вашего Института или Факультета:",
    "reg_success":      "✅ Регистрация успешна! Добро пожаловать в главное меню.",
    "main_menu":        "Выберите действие:",
    "task":             "📋 Ваше задание:\n\n{task_text}",
    "task_sent":        "✅ Задание отправлено на проверку!",
    "task_refused":     "Задание отклонено. Выберите новое действие в меню.",
    "question_sent":    "✅ Вопрос отправлен, ожидайте ответа.",
    "admin_menu":       "🛡 Панель администратора:",
    "no_pending_tasks": "Нет заданий на проверку.",
    "no_questions":     "Нет новых вопросов.",
    "grade_success":    "Оценка {grade} выставлена.",
    "user_grade_notify":"🎉 Ура! Ты получил {grade} баллов за задание!",
    "user_rework_notify":"📝 Твое задание было отправлено на доработку.",
    "answer_sent":      "Ответ отправлен пользователю.",
    "need_register":    "Сначала зарегистрируйтесь через /start",
}

# ============================================================================
# FSM STATES
# ============================================================================

class RegistrationForm(StatesGroup):
    name      = State()
    vk        = State()
    institute = State()


class QuestionForm(StatesGroup):
    text = State()


class TaskForm(StatesGroup):
    answer_type    = State()
    answer_content = State()


class AdminAnswerForm(StatesGroup):
    waiting_answer = State()

# ============================================================================
# JSON STORAGE — низкоуровневые операции
# ============================================================================

async def _read_json(path: str) -> dict | list:
    """Читает JSON-файл. Возвращает пустой dict/list если файл не существует."""
    if not os.path.exists(path):
        # Выбираем тип по тому, какой файл читаем
        return [] if path in (TASKS_FILE, QUESTIONS_FILE) else {}
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        content = await f.read()
    return json.loads(content) if content.strip() else ({} if path not in (TASKS_FILE, QUESTIONS_FILE) else [])


async def _write_json(path: str, data: dict | list) -> None:
    """Атомарно записывает данные в JSON-файл."""
    os.makedirs(DATA_DIR, exist_ok=True)
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))


async def _next_id(entity: str) -> int:
    """Возвращает следующий автоинкремент для указанной сущности."""
    counters = await _read_json(COUNTERS_FILE)
    counters[entity] = counters.get(entity, 0) + 1
    await _write_json(COUNTERS_FILE, counters)
    return counters[entity]

# ============================================================================
# JSON STORAGE — бизнес-операции
# ============================================================================

async def db_add_user(tg_id: int, name: str, vk: str, institute: str) -> None:
    users: dict = await _read_json(USERS_FILE)
    users[str(tg_id)] = {
        "tg_id":        tg_id,
        "name":         name,
        "vk_link":      vk,
        "institute":    institute,
        "rating_score": 0,
        "created_at":   datetime.now().isoformat(),
    }
    await _write_json(USERS_FILE, users)


async def db_get_user(tg_id: int) -> dict | None:
    users: dict = await _read_json(USERS_FILE)
    return users.get(str(tg_id))


async def db_get_all_users() -> list[dict]:
    users: dict = await _read_json(USERS_FILE)
    return sorted(users.values(), key=lambda u: u["created_at"], reverse=True)


async def db_get_top_users(limit: int = 5) -> list[dict]:
    users: dict = await _read_json(USERS_FILE)
    return sorted(users.values(), key=lambda u: u["rating_score"], reverse=True)[:limit]


def get_random_task_template() -> dict:
    return random.choice(TASK_TEMPLATES)


async def db_create_user_task(user_id: int, template_id: int, status: str = "viewing") -> int:
    tasks: list = await _read_json(TASKS_FILE)
    task_id = await _next_id("user_tasks")
    tasks.append({
        "id":          task_id,
        "user_id":     user_id,
        "template_id": template_id,
        "status":      status,
        "user_answer": None,
        "answer_type": None,
        "admin_grade": None,
        "created_at":  datetime.now().isoformat(),
    })
    await _write_json(TASKS_FILE, tasks)
    return task_id


async def db_delete_task(task_id: int) -> None:
    """Удаляет задание (например, при отказе участника)."""
    tasks: list = await _read_json(TASKS_FILE)
    tasks = [t for t in tasks if t["id"] != task_id]
    await _write_json(TASKS_FILE, tasks)


async def db_update_task_answer(task_id: int, answer: str, answer_type: str) -> None:
    tasks: list = await _read_json(TASKS_FILE)
    for task in tasks:
        if task["id"] == task_id:
            task["user_answer"] = answer
            task["answer_type"] = answer_type
            task["status"]      = "pending_review"
            break
    await _write_json(TASKS_FILE, tasks)


async def db_get_pending_tasks() -> list[dict]:
    tasks: list = await _read_json(TASKS_FILE)
    users: dict = await _read_json(USERS_FILE)
    result = []
    for t in tasks:
        if t["status"] != "pending_review":
            continue
        user = users.get(str(t["user_id"]), {})
        template = next((tmpl for tmpl in TASK_TEMPLATES if tmpl["id"] == t["template_id"]), {})
        result.append({**t, "name": user.get("name", "—"), "user_tg_id": t["user_id"],
                        "task_text": template.get("text", "")})
    return sorted(result, key=lambda x: x["created_at"])


async def db_grade_task(task_id: int, grade: int) -> int | bool | None:
    """
    Выставляет оценку.
    Возвращает:
    - tg_id пользователя (int), если успех
    - False, если задание уже проверено другим админом
    - None, если задание не найдено
    """
    tasks: list = await _read_json(TASKS_FILE)
    user_id = None

    for task in tasks:
        if task["id"] == task_id:
            # ЗАЩИТА: проверяем, не проверил ли уже кто-то другой
            if task["status"] != "pending_review":
                return False  # Задание уже оценено

            task["admin_grade"] = grade
            task["status"] = "completed"
            user_id = task["user_id"]
            break

    if user_id is None:
        return None

    await _write_json(TASKS_FILE, tasks)

    if grade > 0:
        users: dict = await _read_json(USERS_FILE)
        key = str(user_id)
        if key in users:
            users[key]["rating_score"] += grade
            await _write_json(USERS_FILE, users)

    return user_id


async def db_get_task_info(task_id: int) -> dict | None:
    tasks: list = await _read_json(TASKS_FILE)
    users: dict = await _read_json(USERS_FILE)
    for t in tasks:
        if t["id"] == task_id:
            template = next((tmpl for tmpl in TASK_TEMPLATES if tmpl["id"] == t["template_id"]), {})
            return {**t, "user_tg_id": t["user_id"], "task_text": template.get("text", "")}
    return None


async def db_add_question(user_id: int, text: str) -> None:
    questions: list = await _read_json(QUESTIONS_FILE)
    q_id = await _next_id("questions")
    questions.append({
        "id":          q_id,
        "user_id":     user_id,
        "text":        text,
        "answer_text": None,
        "status":      "new",
        "created_at":  datetime.now().isoformat(),
    })
    await _write_json(QUESTIONS_FILE, questions)


async def db_get_new_questions() -> list[dict]:
    questions: list = await _read_json(QUESTIONS_FILE)
    users: dict     = await _read_json(USERS_FILE)
    result = []
    for q in questions:
        if q["status"] != "new":
            continue
        user = users.get(str(q["user_id"]), {})
        result.append({**q, "name": user.get("name", "—"), "user_tg_id": q["user_id"]})
    return sorted(result, key=lambda x: x["created_at"])


async def db_answer_question(question_id: int, answer_text: str) -> int | None:
    """Отвечает на вопрос. Возвращает tg_id пользователя или None."""
    questions: list = await _read_json(QUESTIONS_FILE)
    user_id = None
    for q in questions:
        if q["id"] == question_id:
            q["answer_text"] = answer_text
            q["status"]      = "answered"
            user_id = q["user_id"]
            break
    if user_id is not None:
        await _write_json(QUESTIONS_FILE, questions)
    return user_id

# ============================================================================
# KEYBOARDS
# ============================================================================

def get_privacy_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Согласен",    callback_data="privacy_agree")
    builder.button(text="❌ Не согласен", callback_data="privacy_disagree")
    return builder.as_markup()


def get_main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📝 Выполнить задание")
    builder.button(text="❓ Задать вопрос организатору")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def get_task_action_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Выполнить",  callback_data="task_do")
    builder.button(text="❌ Отказаться", callback_data="task_refuse")
    return builder.as_markup()


def get_answer_type_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Текстовый ответ", callback_data="ans_text")
    builder.button(text="📎 Прикрепить медиа", callback_data="ans_media")
    return builder.as_markup()


def get_admin_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Список участников",  callback_data="adm_users")
    builder.button(text="🏆 Топ-5 рейтинга",     callback_data="adm_top")
    builder.button(text="📋 Проверить задания",   callback_data="adm_check_tasks")
    builder.button(text="💬 Ответить на вопросы", callback_data="adm_questions")
    builder.adjust(2)
    return builder.as_markup()


def get_grading_kb(task_id: int):
    builder = InlineKeyboardBuilder()
    for i in range(1, 11):
        builder.button(text=str(i), callback_data=f"grade_{task_id}_{i}")
    builder.button(text="🔄 Отправить на доработку", callback_data=f"grade_{task_id}_rework")
    builder.adjust(5)
    return builder.as_markup()


def get_question_list_kb(questions: list[dict]):
    builder = InlineKeyboardBuilder()
    for q in questions:
        builder.button(text=f"❓ Вопрос от {q['name']}", callback_data=f"adm_q_{q['id']}")
    builder.adjust(1)
    return builder.as_markup()


def get_back_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data="admin_menu")
    return builder.as_markup()

# ============================================================================
# FILTER
# ============================================================================

class IsAdmin(BaseFilter):
    async def __call__(self, event: types.Message | types.CallbackQuery) -> bool:
        return event.from_user.id in ADMINS

# ============================================================================
# USER HANDLERS
# ============================================================================

async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS["start"])
    await message.answer(TEXTS["privacy"], reply_markup=get_privacy_kb())


async def privacy_agree(callback: types.CallbackQuery, state: FSMContext):
    user = await db_get_user(callback.from_user.id)
    if user:
        # Уже зарегистрирован — просто открываем меню
        await callback.message.edit_text("Вы уже зарегистрированы! Добро пожаловать.")
        await callback.message.answer(TEXTS["main_menu"], reply_markup=get_main_menu_kb())
        return
    await callback.message.edit_text(TEXTS["reg_name"])
    await state.set_state(RegistrationForm.name)


async def privacy_disagree(callback: types.CallbackQuery):
    await callback.message.edit_text(TEXTS["access_denied"])


async def reg_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("ФИО не может быть пустым. Попробуйте снова:")
        return
    await state.update_data(name=name)
    await message.answer(TEXTS["reg_vk"])
    await state.set_state(RegistrationForm.vk)


async def reg_vk(message: types.Message, state: FSMContext):
    vk = message.text.strip()
    if not vk:
        await message.answer("Ссылка ВКонтакте не может быть пустой. Попробуйте снова:")
        return
    await state.update_data(vk=vk)
    await message.answer(TEXTS["reg_institute"])
    await state.set_state(RegistrationForm.institute)


async def reg_institute(message: types.Message, state: FSMContext):
    institute = message.text.strip()
    if not institute:
        await message.answer("Название института не может быть пустым. Попробуйте снова:")
        return
    data = await state.get_data()
    await db_add_user(message.from_user.id, data["name"], data["vk"], institute)
    await state.clear()

    final_text = (
        f"{TEXTS['reg_success']}\n\n"
        f"👤 Имя: {data['name']}\n"
        f"🔗 ВКонтакте: {data['vk']}\n"
        f"🏛 Институт/Факультет: {institute}"
    )
    await message.answer(final_text, reply_markup=get_main_menu_kb())


async def do_task(message: types.Message, state: FSMContext):
    user = await db_get_user(message.from_user.id)
    if not user:
        await message.answer(TEXTS["need_register"])
        return
    task_template = get_random_task_template()
    task_id = await db_create_user_task(message.from_user.id, task_template["id"])
    await state.update_data(current_task_id=task_id, task_text=task_template["text"])
    await message.answer(
        TEXTS["task"].format(task_text=task_template["text"]),
        reply_markup=get_task_action_kb()
    )


async def task_refuse(callback: types.CallbackQuery, state: FSMContext):
    # Исправлено: удаляем висящее задание со статусом "viewing"
    data = await state.get_data()
    task_id = data.get("current_task_id")
    if task_id:
        await db_delete_task(task_id)
    await state.clear()
    await callback.message.edit_text(TEXTS["task_refused"])


async def task_do(callback: types.CallbackQuery, state: FSMContext):
    # Получаем данные из машины состояний
    data = await state.get_data()
    # Достаем текст задания (или заглушку, если вдруг его там нет)
    task_text = data.get("task_text", "Текст задания потерян 😔")

    # Формируем новый текст, который включает и само задание, и новый вопрос
    new_message_text = (
        f"📋 Ваше задание:\n\n{task_text}\n\n"
        f"👇 Отлично! Выберите формат ответа:"
    )

    await callback.message.edit_text(
        new_message_text,
        reply_markup=get_answer_type_kb()
    )
    await state.set_state(TaskForm.answer_type)


async def answer_type_selected(callback: types.CallbackQuery, state: FSMContext):
    ans_type = callback.data.split("_")[1]  # "text" или "media"
    await state.update_data(answer_type=ans_type)
    if ans_type == "text":
        await callback.message.edit_text("📝 Отправьте текст ответа:")
    else:
        await callback.message.edit_text("📎 Отправьте фото/файл с ответом:")
    await state.set_state(TaskForm.answer_content)


async def receive_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    answer_type = data.get("answer_type", "text")

    if answer_type == "text":
        if not message.text:
            await message.answer("❌ Пожалуйста, отправьте текстовый ответ.")
            return
        content = message.text
    else:
        if message.photo:
            content = message.photo[-1].file_id
        elif message.document:
            content = message.document.file_id
        elif message.video:
            content = message.video.file_id
        else:
            await message.answer("❌ Пожалуйста, отправьте фото, видео или документ.")
            return

    task_id = data.get("current_task_id")
    if task_id:
        await db_update_task_answer(task_id, content, answer_type)
    await state.clear()
    await message.answer(TEXTS["task_sent"], reply_markup=get_main_menu_kb())


async def ask_question(message: types.Message, state: FSMContext):
    user = await db_get_user(message.from_user.id)
    if not user:
        await message.answer(TEXTS["need_register"])
        return
    await message.answer("💬 Введите ваш вопрос:")
    await state.set_state(QuestionForm.text)


async def process_question(message: types.Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Вопрос не может быть пустым.")
        return
    await db_add_question(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer(TEXTS["question_sent"])

# ============================================================================
# ADMIN HANDLERS
# ============================================================================

async def cmd_admin(message: types.Message):
    await message.answer(TEXTS["admin_menu"], reply_markup=get_admin_kb())


async def adm_users(callback: types.CallbackQuery):
    users = await db_get_all_users()
    if not users:
        text = "Пока нет зарегистрированных пользователей."
    else:
        lines = []
        for u in users:
            lines.append(f"🆔 {u['tg_id']} | 👤 {u['name']} | 🏫 {u['institute']} | ⭐ {u['rating_score']}")
        text = "👥 Список участников:\n\n" + "\n".join(lines)
    await callback.message.answer(text, reply_markup=get_back_kb())
    await callback.answer()


async def adm_top(callback: types.CallbackQuery):
    users = await db_get_top_users()
    if not users:
        text = "Пока нет данных для рейтинга."
    else:
        lines = [f"{i}. {u['name']} — {u['rating_score']} баллов" for i, u in enumerate(users, 1)]
        text = "🏆 Топ-5 рейтинга:\n\n" + "\n".join(lines)
    await callback.message.answer(text, reply_markup=get_back_kb())
    await callback.answer()


async def adm_check_tasks(callback: types.CallbackQuery):
    tasks = await db_get_pending_tasks()
    if not tasks:
        await callback.answer(TEXTS["no_pending_tasks"], show_alert=True)
        return
    task = tasks[0]
    if task["answer_type"] == "text":
        answer_preview = (task["user_answer"] or "")[:500]
    else:
        answer_preview = "📎 Медиафайл (прикреплён)"
    text = (
        f"📋 Проверка задания #{task['id']}\n\n"
        f"👤 Студент: {task['name']}\n"
        f"🆔 ID: {task['user_tg_id']}\n"
        f"📝 Задание: {task['task_text'][:300]}\n\n"
        f"💬 Ответ:\n{answer_preview}"
    )
    await callback.message.answer(text, reply_markup=get_grading_kb(task["id"]))
    await callback.answer()


async def process_grade(callback: types.CallbackQuery, bot: Bot):
    parts = callback.data.split("_")  # grade_{task_id}_{value}
    task_id = int(parts[1])
    grade_val = parts[2]

    if grade_val == "rework":
        final_grade = 0
        notify_msg = TEXTS["user_rework_notify"]
        grade_label = "на доработку"
    else:
        final_grade = int(grade_val)
        notify_msg = TEXTS["user_grade_notify"].format(grade=final_grade)
        grade_label = grade_val

    result = await db_grade_task(task_id, final_grade)

    # Обрабатываем ситуацию, когда другой админ уже оценил
    if result is False:
        await callback.message.edit_text("⚠️ Кто-то из коллег уже оценил это задание!")
        await callback.answer("Задание уже проверено", show_alert=True)
        return
    elif result is None:
        await callback.answer("Ошибка: задание не найдено.", show_alert=True)
        return

    user_id = result  # Если проверки пройдены, значит тут tg_id пользователя

    await callback.message.edit_text(f"✅ Оценка «{grade_label}» выставлена.")
    await callback.answer(TEXTS["grade_success"].format(grade=grade_label))

    try:
        await bot.send_message(user_id, notify_msg)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление пользователю {user_id}: {e}")


async def adm_questions(callback: types.CallbackQuery):
    questions = await db_get_new_questions()
    if not questions:
        await callback.answer(TEXTS["no_questions"], show_alert=True)
        return
    await callback.message.answer(
        "💬 Список новых вопросов:",
        reply_markup=get_question_list_kb(questions)
    )
    await callback.answer()


async def adm_select_question(callback: types.CallbackQuery, state: FSMContext):
    q_id = int(callback.data.split("_")[2])  # adm_q_{id}

    # Показываем текст вопроса
    questions = await db_get_new_questions()
    question  = next((q for q in questions if q["id"] == q_id), None)
    if question:
        await callback.message.answer(
            f"❓ Вопрос от {question['name']}:\n\n{question['text']}\n\n✍️ Введите ответ:"
        )
    else:
        await callback.message.answer("✍️ Введите ответ пользователю:")

    await state.update_data(question_id=q_id)
    await state.set_state(AdminAnswerForm.waiting_answer)
    await callback.answer()


async def admin_send_answer(message: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    q_id = data.get("question_id")
    if not q_id:
        await message.answer("❌ Ошибка: вопрос не найден. Попробуйте снова.")
        await state.clear()
        return

    user_id = await db_answer_question(q_id, message.text)
    await state.clear()

    if user_id:
        try:
            await bot.send_message(user_id, f"📬 Ответ на ваш вопрос:\n\n{message.text}")
        except Exception as e:
            logger.error(f"Не удалось отправить ответ пользователю {user_id}: {e}")

    await message.answer(TEXTS["answer_sent"], reply_markup=get_back_kb())


async def admin_menu_back(callback: types.CallbackQuery):
    await callback.message.edit_text(TEXTS["admin_menu"], reply_markup=get_admin_kb())
    await callback.answer()

# ============================================================================
# REGISTER HANDLERS
# ============================================================================

def register_handlers(dp: Dispatcher):
    # --- Старт и политика ---
    dp.message.register(cmd_start, Command("start"))
    dp.callback_query.register(privacy_agree,    F.data == "privacy_agree")
    dp.callback_query.register(privacy_disagree, F.data == "privacy_disagree")

    # --- Регистрация ---
    dp.message.register(reg_name,      RegistrationForm.name)
    dp.message.register(reg_vk,        RegistrationForm.vk)
    dp.message.register(reg_institute, RegistrationForm.institute)

    # --- Задания ---
    dp.message.register(do_task, F.text == "📝 Выполнить задание")
    dp.callback_query.register(task_refuse,          F.data == "task_refuse")
    dp.callback_query.register(task_do,              F.data == "task_do")
    dp.callback_query.register(answer_type_selected, F.data.startswith("ans_"))
    dp.message.register(receive_answer,              TaskForm.answer_content)

    # --- Вопросы ---
    # Исправлено: текст кнопки теперь совпадает с тем, что в клавиатуре
    dp.message.register(ask_question,     F.text == "❓ Задать вопрос организатору")
    dp.message.register(process_question, QuestionForm.text)

    # --- Админ ---
    dp.message.register(cmd_admin,           Command("admin"), IsAdmin())
    dp.callback_query.register(adm_users,        F.data == "adm_users",        IsAdmin())
    dp.callback_query.register(adm_top,          F.data == "adm_top",           IsAdmin())
    dp.callback_query.register(adm_check_tasks,  F.data == "adm_check_tasks",   IsAdmin())
    dp.callback_query.register(process_grade,    F.data.startswith("grade_"),   IsAdmin())
    dp.callback_query.register(adm_questions,    F.data == "adm_questions",     IsAdmin())
    dp.callback_query.register(adm_select_question, F.data.startswith("adm_q_"), IsAdmin())
    dp.message.register(admin_send_answer,       AdminAnswerForm.waiting_answer, IsAdmin())
    dp.callback_query.register(admin_menu_back,  F.data == "admin_menu",        IsAdmin())

# ============================================================================
# MAIN
# ============================================================================

async def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher()
    register_handlers(dp)
    logger.info("Бот запущен...")
    logger.info(f"Админы: {ADMINS}")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())


