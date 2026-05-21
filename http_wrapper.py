#!/usr/bin/env python3
"""
Единый файл для Bothost
Все секреты — через переменные окружения
"""

import asyncio
import logging
import os
import re
from aiohttp import web
from exchangelib import Account, Credentials, Message, Mailbox, Configuration
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, MessageCreated

# ========== ВСЕ НАСТРОЙКИ — ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIL_LOGIN = os.getenv("MAIL_LOGIN", "s.volkov@caterinburg.ru")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_TO = os.getenv("MAIL_TO", "bp@pfur.ru")
PORT = int(os.environ.get("PORT", 3000))

# Проверка обязательных переменных
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан в переменных окружения")
if not MAIL_PASSWORD:
    raise ValueError("❌ MAIL_PASSWORD не задан в переменных окружения")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ОСТАЛЬНОЙ КОД (БЕЗ ИЗМЕНЕНИЙ) ==========
SIGNATURE = """--
С уважением,
Сергей Волков
Управляющий
117198, г. Москва, ул. Миклухо-Маклая, 6, РУДН
т. сот.: +7 (961) 388-84-82
эл.почта: s.volkov@caterinburg.ru"""

MAPS = {
    "mm6": "https://raw.githubusercontent.com/S-Wolves/MAX_bot/main/%D0%9C%D0%9C6.png",
    "mm10k2": "https://raw.githubusercontent.com/S-Wolves/MAX_bot/main/%D0%9C%D0%9C10%D0%BA2.png",
    "ordzhonikidze": "https://raw.githubusercontent.com/S-Wolves/MAX_bot/main/%D0%9E%D1%80%D0%B4%D0%B6%D0%BE%D0%BD%D0%B8%D0%BA%D0%B8%D0%B4%D0%B7%D0%B5.png",
}

CONTACTS = {
    "mm6": "👥 Контакты склада (Миклухо-Маклая, д.6):<br>• Кладовщик Наталья: <a href=\"tel:+79256050358\">+79256050358</a><br>• Грузчик Сергей: <a href=\"tel:+79269552848\">+79269552848</a>",
    "mm10k2": "👥 Контакты склада (Миклухо-Маклая, д.10к2):<br>• Администратор Илаха: <a href=\"tel:+79778320200\">+79778320200</a><br>• Зав. производства Анна: <a href=\"tel:+79663171768\">+79663171768</a>",
    "ordzhonikidze": "👥 Контакты склада (Орджоникидзе, д.3):<br>• Администратор Екатерина: <a href=\"tel:+79171253314\">+79171253314</a>",
}

def send_email(car_number: str, point_key: str):
    point_addresses = {
        "mm6": "Миклухо-Маклая, д.6",
        "mm10k2": "Миклухо-Маклая, д.10к2",
        "ordzhonikidze": "Орджоникидзе, д.3",
    }
    address = point_addresses.get(point_key, "Неизвестная точка")
    credentials = Credentials(username=MAIL_LOGIN, password=MAIL_PASSWORD)
    try:
        account = Account(primary_smtp_address=MAIL_LOGIN, credentials=credentials, autodiscover=True, access_type='delegate')
    except Exception:
        config = Configuration(server='owa.ekdekb.ru', credentials=credentials)
        account = Account(primary_smtp_address=MAIL_LOGIN, config=config, autodiscover=False, access_type='delegate')
    
    body = f"""
Прошу пропустить машину для разгрузки на {address}.

****************
*     {car_number}     *
****************

Заранее спасибо.

{SIGNATURE}
"""
    msg = Message(account=account, subject=f'Заявка на пропуск {car_number}', body=body, to_recipients=[Mailbox(email_address=MAIL_TO)])
    msg.send()
    logger.info(f"✅ Письмо отправлено для {car_number}")

# ========== HTML-СТРАНИЦА ==========
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>Кейтеринбург — Пропуск</title>
    <style>
        *{box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:16px;background:#f5f5f5}
        .container{max-width:500px;margin:0 auto}h1{font-size:24px;margin-bottom:8px}.subtitle{color:#666;margin-bottom:24px;font-size:14px}
        .points{display:flex;flex-direction:column;gap:12px;margin-bottom:24px}
        .point-btn{background:white;border:1px solid #ddd;border-radius:12px;padding:16px;cursor:pointer}
        .point-btn.selected{background:#007aff;border-color:#007aff;color:white}
        .point-address{font-weight:600}
        .point-note{font-size:12px;opacity:0.7;margin-top:4px}
        .input-group{margin-bottom:16px}
        input{width:100%;padding:14px;border:1px solid #ddd;border-radius:12px;font-size:16px;font-family:monospace;text-transform:uppercase}
        button.submit{width:100%;background:#007aff;color:white;border:none;border-radius:12px;padding:16px;font-size:16px;font-weight:600;cursor:pointer;margin-top:8px}
        .status{margin-top:16px;padding:12px;border-radius:12px;text-align:center;display:none}
        .status.success{background:#d4edda;color:#155724}
        .status.error{background:#f8d7da;color:#721c24}
        .status.loading{background:#e2f0ff;color:#004085}
        .result{margin-top:20px;padding:16px;background:white;border-radius:12px;border:1px solid #ddd;display:none}
        .result img{max-width:100%;border-radius:8px;margin-bottom:12px;cursor:pointer}
        .contacts a{color:#007aff;text-decoration:none}
        .footer{font-size:12px;color:#999;text-align:center;margin-top:24px}
    </style>
</head>
<body>
<div class="container">
    <h1>🚚 РУДН</h1>
    <div class="subtitle">ООО "Здоровое питание" — Оформление пропуска</div>
    <div class="points">
        <button class="point-btn" data-point="mm6" data-name="Миклухо-Маклая, д.6"><div class="point-address">🏢 Миклухо-Маклая, д.6</div><div class="point-note">Въезд в подземную парковку</div></button>
        <button class="point-btn" data-point="mm10k2" data-name="Миклухо-Маклая, д.10к2"><div class="point-address">🏢 Миклухо-Маклая, д.10к2</div></button>
        <button class="point-btn" data-point="ordzhonikidze" data-name="Орджоникидзе, д.3"><div class="point-address">🏢 Орджоникидзе, д.3</div></button>
    </div>
    <div class="input-group"><label>🚛 Номер автомобиля</label><input type="text" id="plate" placeholder="А123ВС777" autocomplete="off"></div>
    <button class="submit" id="submitBtn">Оформить пропуск</button>
    <div id="status" class="status"></div>
    <div id="result" class="result"><div id="resultMap"></div><div id="resultContacts" class="contacts"></div></div>
    <div class="footer">Пропуск действует 24 часа</div>
</div>
<script>
    const btns=document.querySelectorAll('.point-btn');const plate=document.getElementById('plate');const submit=document.getElementById('submitBtn');
    const statusDiv=document.getElementById('status');const resultDiv=document.getElementById('result');const resultMap=document.getElementById('resultMap');
    const resultContacts=document.getElementById('resultContacts');let selected=null;
    function show(m,t){statusDiv.textContent=m;statusDiv.className=`status ${t}`;statusDiv.style.display='block';setTimeout(()=>statusDiv.style.display='none',3000);}
    plate.addEventListener('input',e=>e.target.value=e.target.value.toUpperCase());
    btns.forEach(btn=>btn.addEventListener('click',()=>{btns.forEach(b=>b.classList.remove('selected'));btn.classList.add('selected');selected=btn.dataset.point;resultDiv.style.display='none';}));
    submit.addEventListener('click',async()=>{
        const plateVal=plate.value.trim().replace(/\\s+/g,'').replace(/-/g,'');
        if(!selected){show('Выберите точку разгрузки','error');return;}
        if(!plateVal){show('Введите номер автомобиля','error');return;}
        const regex=/^[АВЕКМНОРСТУХ]\\d{3}[АВЕКМНОРСТУХ]{2,3}\\d{2,3}$/i;
        if(!regex.test(plateVal)){show('Неверный формат номера. Пример: А123ВС777','error');return;}
        submit.disabled=true;show('Отправка...','loading');
        try{
            const res=await fetch('/api/request-pass',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({point_key:selected,car_number:plateVal})});
            const data=await res.json();
            if(res.ok){
                show('✅ Заявка отправлена!','success');
                if(data.map_url)resultMap.innerHTML=`<img src="${data.map_url}" alt="Схема" onclick="window.open('${data.map_url}','_blank')">`;
                if(data.contacts)resultContacts.innerHTML=data.contacts;
                resultDiv.style.display='block';
                btns.forEach(b=>b.classList.remove('selected'));selected=null;plate.value='';
            }else show(data.error||'Ошибка','error');
        }catch(e){show('Ошибка соединения','error');}
        finally{submit.disabled=false;}
    });
</script>
</body>
</html>"""

# ========== ВЕБ-СЕРВЕР ==========
async def web_handler():
    app = web.Application()
    
    async def handle_index(request):
        return web.Response(text=HTML_PAGE, content_type='text/html')
    
    async def handle_health(request):
        return web.Response(text="OK")
    
    async def handle_api(request):
        try:
            data = await request.json()
            car_number = data.get('car_number', '').upper()
            point_key = data.get('point_key')
            if not car_number or not point_key:
                return web.json_response({'error': 'Не все данные'}, status=400)
            if not re.match(r"^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2,3}\d{2,3}$", car_number):
                return web.json_response({'error': 'Неверный формат номера'}, status=400)
            send_email(car_number, point_key)
            return web.json_response({'status': 'ok', 'map_url': MAPS.get(point_key, ""), 'contacts': CONTACTS.get(point_key, "")})
        except Exception as e:
            logger.error(f"API error: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    app.router.add_get('/', handle_index)
    app.router.add_get('/health', handle_health)
    app.router.add_post('/api/request-pass', handle_api)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"🌐 Веб-сервер запущен на порту {PORT}")
    while True:
        await asyncio.sleep(3600)

# ========== БОТ ==========
greeted_users = set()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_user_id_from_event(event):
    try:
        if hasattr(event, 'message') and hasattr(event.message, 'sender'):
            return getattr(event.message.sender, 'user_id', None) or getattr(event.message.sender, 'id', None)
        if hasattr(event, 'user'):
            return getattr(event.user, 'user_id', None) or getattr(event.user, 'id', None)
        if hasattr(event, 'chat_id'):
            return event.chat_id
        return None
    except Exception:
        return None

@dp.bot_started()
async def bot_started(event: BotStarted):
    greeted_users.add(event.chat_id)
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="🚚 **Кейтеринбург**\n\nДобро пожаловать! 👇 Нажмите на кнопку слева от строки ввода, чтобы открыть форму заказа пропуска."
    )

@dp.message_created(F.message.body.text)
async def handle_message(event: MessageCreated):
    user_id = get_user_id_from_event(event)
    if not user_id:
        return
    text = event.message.body.text.strip()
    logger.info(f"Сообщение: '{text}'")
    if text == '/start':
        greeted_users.add(user_id)
        await event.message.answer("🚚 **Кейтеринбург**\n\n👇 Нажмите на кнопку слева от строки ввода, чтобы открыть форму заказа пропуска.")
    elif user_id in greeted_users:
        await event.message.answer("👇 Нажмите на кнопку слева от строки ввода, чтобы открыть форму заказа пропуска.")
    else:
        greeted_users.add(user_id)
        await event.message.answer("🚚 **Кейтеринбург**\n\n👇 Нажмите на кнопку слева от строки ввода, чтобы открыть форму заказа пропуска.")

# ========== ЗАПУСК ==========
async def main():
    logger.info("🚀 Запуск единого сервера...")
    await bot.delete_webhook()
    asyncio.create_task(web_handler())
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logger.error(f"❌ Ошибка polling: {e}, перезапуск через 5 секунд...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
