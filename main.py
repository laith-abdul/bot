#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
بوت تلجرام لفصل مسارات الأغاني (موسيقى/صوت/فصل كامل) باستخدام Demucs

الميزات:
- استقبال ملف صوتي/فيديو، أو رابط (يوتيوب/تيك توك/إنستقرام/فيسبوك/ساوندكلاود...)
- معاينة الرابط (العنوان، المدة، صورة مصغرة) وطلب تأكيد قبل التحميل
- قص جزء اختياري من المقطع قبل المعالجة
- اختيار نوع الفصل: موسيقى فقط / صوت المغني فقط / فصل كامل لكل الآلات
- اختيار جودة المعالجة: سريع أو دقيق (نموذجين مختلفين من Demucs)
- اختيار صيغة الملف الناتج: mp3 / wav / flac
- شريط تقدم حقيقي أثناء معالجة Demucs
- تخزين مؤقت (Cache) للنتائج لتفادي إعادة المعالجة لنفس الطلب
- حد للمعالجة المتزامنة عبر Semaphore لتفادي إرهاق الجهاز
- دعم عربي/إنجليزي/كردي حسب لغة تلجرام للمستخدم

ملاحظة حقوق الملكية: هذا البوت مخصص للاستخدام على محتوى تملكه أو له ترخيص يسمح بذلك.
احترم شروط استخدام المنصات وحقوق الملكية الفكرية.
"""

import os
import re
import json
import time
import hashlib
import logging
import asyncio
import threading
import subprocess
import shutil
import uuid
from enum import IntEnum
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.error import TimedOut, NetworkError
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

import yt_dlp

from i18n import t, get_lang, stem_name, DEFAULT_LANG

# ---------------------------------------------------------------------------
# الإعدادات
# ---------------------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError(
        "لم يتم تعيين متغير البيئة BOT_TOKEN. عرّفه قبل تشغيل البوت، مثال:\n"
        "  export BOT_TOKEN=\"123456:ABC-your-token-here\"\n"
        "⚠️ لا تضع التوكن مباشرة داخل الكود، خصوصاً إذا كنت ستشارك الملف مع أي جهة."
    )

# =============================================================================
# إعداد البروكسي (SOCKS5) — اختياري، فقط إذا كان تلجرام محجوباً/مقطوعاً بشبكتك
# =============================================================================
# أسهل طريقة: عبّئ القيمة التالية مباشرة هنا بدل استخدام متغيرات بيئة بالطرفية.
# اتركها فارغة "" إذا ما عندك بروكسي، أو إذا تفضّل ضبطها عبر متغيرات البيئة بالأسفل.
# مثال بصيغة رابط كامل: "socks5://username:password@1.2.3.4:1080"
# مثال بدون مصادقة:      "socks5://1.2.3.4:1080"
HARDCODED_PROXY_URL = "http://gn3ruprz:Pk0CNgFaDazk@208.68.161.174:9002"

# اختياري: نفس الإعداد لكن عبر متغير بيئة TELEGRAM_PROXY_URL (له أولوية أعلى من
# HARDCODED_PROXY_URL أعلاه إذا كان الاثنان معبّأين، مفيد عند التشغيل على سيرفر
# لا تريد تعديل الكود عليه مباشرة)
TELEGRAM_PROXY_URL = os.environ.get("TELEGRAM_PROXY_URL", "").strip() or HARDCODED_PROXY_URL

# إعدادات بديلة ومريحة لبناء رابط بروكسي SOCKS5 تلقائياً دون كتابة الرابط كاملاً يدوياً
SOCKS5_HOST = os.environ.get("SOCKS5_HOST", "").strip()
SOCKS5_PORT = os.environ.get("SOCKS5_PORT", "").strip()
SOCKS5_USERNAME = os.environ.get("SOCKS5_USERNAME", "").strip()
SOCKS5_PASSWORD = os.environ.get("SOCKS5_PASSWORD", "").strip()

if not TELEGRAM_PROXY_URL and SOCKS5_HOST and SOCKS5_PORT:
    _auth = f"{SOCKS5_USERNAME}:{SOCKS5_PASSWORD}@" if SOCKS5_USERNAME else ""
    TELEGRAM_PROXY_URL = f"socks5://{_auth}{SOCKS5_HOST}:{SOCKS5_PORT}"

# إذا كان البروكسي المُعطى من نوع SOCKS، تأكد أن حزمة socksio مثبّتة (متطلَّبة من httpx
# للتعامل مع socks5://)، وإلا يفشل الاتصال ببوت غامض عند التشغيل. نتحقق مبكراً برسالة
# واضحة بدل ترك المستخدم يواجه خطأ استيراد غير مفهوم لاحقاً
if TELEGRAM_PROXY_URL.startswith("socks"):
    try:
        import socksio  # noqa: F401
    except ImportError as _e:
        raise RuntimeError(
            "تم تفعيل بروكسي SOCKS5 (TELEGRAM_PROXY_URL/SOCKS5_HOST) لكن حزمة socksio "
            "غير مثبّتة، وهي مطلوبة لدعم SOCKS5. ثبّتها عبر:\n"
            "  pip install \"python-telegram-bot[socks]\"\n"
            "ثم أعد تشغيل البوت."
        ) from _e

# بروكسي منفصل تماماً (اختياري) لتحميلات yt-dlp من الروابط الخارجية (يوتيوب/تيك توك/
# إلخ). فارغ افتراضياً، أي أن التحميل يتم مباشرة بدون بروكسي حتى لو كان بروكسي تلجرام
# مفعّلاً أعلاه — لأن مشاكل الرفع لتلجرام ومشاكل التحميل الخارجي غالباً مختلفة السبب
YTDLP_PROXY_URL = os.environ.get("YTDLP_PROXY_URL", "").strip()

# مهلة القراءة لكل اتصال فرعي أثناء تحميل yt-dlp، ومحاولات إعادة عند انقطاع مؤقت.
# القيم الافتراضية بالمكتبة قد تكون قصيرة جداً لملفات/مقاطع طويلة على اتصال متوسط
YTDLP_SOCKET_TIMEOUT = float(os.environ.get("YTDLP_SOCKET_TIMEOUT", "60"))
YTDLP_RETRIES = int(os.environ.get("YTDLP_RETRIES", "10"))

# مهلة الاتصال بسيرفرات تلجرام بالثواني
TELEGRAM_CONNECT_TIMEOUT = float(os.environ.get("TELEGRAM_CONNECT_TIMEOUT", "30"))
TELEGRAM_READ_TIMEOUT = float(os.environ.get("TELEGRAM_READ_TIMEOUT", "60"))

# مهلة مخصصة لرفع الملفات الصوتية الناتجة (أطول من المهلة العادية لأن الملفات قد تكون
# كبيرة نسبياً والاتصال قد يكون بطيئاً)؛ زدها إذا كان اتصالك بالإنترنت بطيئاً
TELEGRAM_UPLOAD_TIMEOUT = float(os.environ.get("TELEGRAM_UPLOAD_TIMEOUT", "300"))

# عدد محاولات إعادة إرسال الملف عند فشل الرفع بسبب انقطاع أو بطء مؤقت في الشبكة
UPLOAD_MAX_RETRIES = int(os.environ.get("UPLOAD_MAX_RETRIES", "5"))

# مهلة الحصول على اتصال حر من مجمّع الاتصالات (connection pool)؛ القيمة الافتراضية في
# المكتبة قصيرة جداً (1 ثانية) وقد تُسبب أخطاء اتصال إضافية أثناء رفع ملفات كبيرة
TELEGRAM_POOL_TIMEOUT = float(os.environ.get("TELEGRAM_POOL_TIMEOUT", "60"))

# مهلة كتابة/رفع المحتوى الفعلي للملفات (media). هذه المهلة منفصلة داخلياً عن
# write_timeout العادي، ويجب ضبطها صراحة وإلا تُستخدم قيمة افتراضية قصيرة (20 ثانية)
# غير كافية إطلاقاً لرفع فيديو كبير على اتصال بطيء
TELEGRAM_MEDIA_WRITE_TIMEOUT = float(os.environ.get("TELEGRAM_MEDIA_WRITE_TIMEOUT", str(TELEGRAM_UPLOAD_TIMEOUT)))

# تحذير المستخدم إذا تجاوز حجم الفيديو الناتج هذا الحد (بالميجابايت)؛ تلجرام يسمح
# للبوتات برفع ملفات حتى 50 ميجابايت تقريباً عبر Bot API السحابي العادي
MAX_VIDEO_SEND_SIZE_MB = int(os.environ.get("MAX_VIDEO_SEND_SIZE_MB", "45"))

# عدد محاولات إعادة الاتصال بتلجرام عند بدء تشغيل البوت إذا فشل الاتصال الأول (شبكة متقطعة)
STARTUP_MAX_RETRIES = int(os.environ.get("STARTUP_MAX_RETRIES", "5"))
STARTUP_RETRY_DELAY = float(os.environ.get("STARTUP_RETRY_DELAY", "15"))

# مجلدات العمل
BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "temp_jobs"
WORK_DIR.mkdir(exist_ok=True)

CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_INDEX_PATH = CACHE_DIR / "index.json"
CACHE_TTL_SECONDS = float(os.environ.get("CACHE_TTL_HOURS", "24")) * 3600
_CACHE_LOCK = threading.Lock()

# نماذج Demucs حسب مستوى الجودة المطلوب
QUALITY_MODELS = {
    "fast": "htdemucs",       # سريع نسبياً وجودته جيدة جداً
    "accurate": "htdemucs_ft",  # نموذج مُحسّن (ensemble)، أبطأ بحوالي 4 أضعاف لكن أدق
}

# الحد الأقصى لحجم الملف الذي يقبله تلجرام للبوتات العادية (بايت) - 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024

# الحد الأقصى لمدة المقطع عند التحميل من رابط (بالثواني). القيمة الافتراضية هنا
# مخفّضة بشكل متحفّظ (6 دقائق بدل 20) لأن الخطة المجانية بأغلب الاستضافات الجاهزة
# (مثل Railway بـ 0.5GB رام) لا تتحمّل معالجة مقاطع طويلة أصلاً بدون OOM Kill.
# ارفعها عبر متغير البيئة MAX_URL_DURATION_SECONDS لو رقّيت الاستضافة لرام أكبر
MAX_URL_DURATION_SECONDS = int(os.environ.get("MAX_URL_DURATION_SECONDS", str(6 * 60)))

# الحد الأقصى لعدد مهام Demucs التي تعمل بنفس الوقت (لتفادي إرهاق الجهاز)
MAX_CONCURRENT_JOBS = int(os.environ.get("MAX_CONCURRENT_JOBS", "1"))

# عدد الأنوية (threads) التي يستخدمها Demucs داخلياً لتسريع معالجة الملف الواحد
# القيمة الافتراضية: عدد أنوية المعالج ناقص واحد (لترك نواة حرة للنظام)، بحد أدنى 1
_default_jobs = max(1, (os.cpu_count() or 2) - 1)
# ملاحظة: تشغيل Demucs بالتوازي (-j) يضاعف استهلاك الرام تقريباً بعدد العمليات، وهذا
# مناسب فقط على سيرفر مخصّص برام وفيرة. على استضافات جاهزة محدودة الموارد (غالبية
# باقات Railway/Render/Heroku المبتدئة توفر 512MB-1GB فقط)، هذا يُسبب قتل العملية
# فجأة من نظام التشغيل (OOM Kill) بمنتصف المعالجة دون أي رسالة خطأ واضحة. لذا
# الافتراضي الآن أصبح متحفظاً (عملية واحدة فقط) إلا لو حدّدت DEMUCS_JOBS يدوياً
# بعد التأكد أن السيرفر يتحمّلها
DEMUCS_JOBS = int(os.environ.get("DEMUCS_JOBS", "1"))

# تقسيم المقطع إلى أجزاء (segments) أثناء الفصل بدل معالجته دفعة واحدة، لتقليل ذروة
# استهلاك الرام بشكل كبير. حسب توثيق Demucs الرسمي: القيم الافتراضية تحتاج ~7GB رام،
# وبقيمة segment=8 يكفي ~3GB فقط. القيمة الافتراضية هنا (6) متحفّظة أكثر لملاءمة
# استضافات بذاكرة محدودة جداً (0.5-1GB). كلما صغرت القيمة قلّت الذاكرة المطلوبة، لكن
# قد تتأثر جودة الفصل قليلاً عند حدود المقاطع الفرعية. عدّلها عبر DEMUCS_SEGMENT
# ملاحظة صريحة: هذا يقلل الذاكرة اللازمة أثناء المعالجة الفعلية فقط، لكن تحميل
# PyTorch ونموذج Demucs نفسه بالذاكرة له حد أدنى ثابت تقريباً بغض النظر عن Segment؛
# على 0.5GB رام إجمالي (تتشارك فيها بايثون ونظام التشغيل أيضاً)، قد لا يكفي حتى مع
# أصغر segment ممكن — إذا استمر الفشل، فالمشكلة عندها حجم الرام نفسه لا الإعدادات
DEMUCS_SEGMENT = os.environ.get("DEMUCS_SEGMENT", "6").strip()

# وضع "الذاكرة المحدودة": فعّله (LOW_MEMORY_MODE=1) على استضافات ضعيفة الرام
# (مثل خطة Railway المجانية 0.5GB). يخفي خيار الجودة "الدقيق" (نموذج ensemble أثقل
# بكثير على الرام والوقت) ويترك فقط الخيار السريع الأخف
LOW_MEMORY_MODE = os.environ.get("LOW_MEMORY_MODE", "1").strip().lower() in ("1", "true", "yes")

# عدد "المراحل" (passes) الداخلية لكل نموذج، يُستخدم لعرض نسبة تقدم إجمالية سلسة
# بدل عرض شريط يرجع للصفر ويعيد العد عند بداية كل مرحلة
MODEL_PASSES = {"fast": 1, "accurate": 4}

URL_PATTERN = re.compile(r"https?://\S+")
TRIM_PATTERN = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)-(\d{1,2}:\d{2}(?::\d{2})?)$")
PROGRESS_PATTERN = re.compile(r"(\d{1,3})%\|")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# قفل يحدد كم مهمة فصل صوت (Demucs) تعمل بنفس الوقت
job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)


async def safe_edit_text(msg, text: str, **kwargs):
    """
    تعديل نص رسالة مع تجاهل خطأ "Message is not modified" الذي يحدث عندما
    يكون النص الجديد مطابقاً تماماً للنص الحالي (تلجرام يرفض التعديل في هذه الحالة)
    """
    try:
        await msg.edit_text(text, **kwargs)
    except Exception as e:
        if "not modified" not in str(e).lower():
            raise


def _upload_backoff_seconds(attempt: int) -> float:
    """
    انتظار متصاعد بين محاولات إعادة الرفع. أخطاء مثل httpx.ReadError/ConnectError
    تعني عادة أن الاتصال انقطع فعلياً (وليس مجرد بطء)، لذا نمنح الشبكة وقتاً أطول
    للتعافي بين المحاولات بدل إعادة المحاولة فوراً بلا فائدة
    """
    return min(60, 8 * attempt)


async def send_audio_with_retry(message, file_path: Path, caption: str):
    """
    إرسال ملف صوتي مع مهلة مخصصة أطول (لأن رفع الملفات يستغرق وقتاً أطول من باقي
    طلبات API) وإعادة محاولة تلقائية عند فشل الرفع بسبب بطء أو انقطاع مؤقت بالشبكة
    """
    last_error = None
    for attempt in range(1, UPLOAD_MAX_RETRIES + 1):
        try:
            with open(file_path, "rb") as fh:
                await message.reply_audio(
                    audio=fh,
                    filename=file_path.name,
                    caption=caption,
                    read_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                    write_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                    connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                    pool_timeout=TELEGRAM_POOL_TIMEOUT,
                )
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "فشلت محاولة رفع الملف %s (محاولة %d/%d): %s: %s",
                file_path.name, attempt, UPLOAD_MAX_RETRIES, type(e).__name__, e,
            )
            if attempt < UPLOAD_MAX_RETRIES:
                await asyncio.sleep(_upload_backoff_seconds(attempt))

    # محاولة أخيرة: إرسال الملف كمستند (document) بدل صوت، فهذا مسار مختلف قد
    # ينجح حتى لو استمر فشل reply_audio تحديداً (يفقد بعض الميزات مثل مشغل الصوت
    # المدمج، لكن أفضل من عدم إيصال الملف للمستخدم إطلاقاً)
    try:
        with open(file_path, "rb") as fh:
            await message.reply_document(
                document=fh,
                filename=file_path.name,
                caption=caption,
                read_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                write_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                pool_timeout=TELEGRAM_POOL_TIMEOUT,
            )
        logger.info("تم إرسال %s كمستند بعد فشل الإرسال كصوت", file_path.name)
        return
    except Exception as e:
        logger.warning("فشلت أيضاً محاولة الإرسال كمستند لـ %s: %s", file_path.name, e)

    raise last_error


async def send_video_with_retry(message, file_path: Path, caption: str):
    """نفس منطق send_audio_with_retry لكن لإرسال فيديو (النتيجة عندما يكون المصدر فيديو)"""
    last_error = None
    for attempt in range(1, UPLOAD_MAX_RETRIES + 1):
        try:
            with open(file_path, "rb") as fh:
                await message.reply_video(
                    video=fh,
                    filename=file_path.name,
                    caption=caption,
                    supports_streaming=True,
                    read_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                    write_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                    connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                    pool_timeout=TELEGRAM_POOL_TIMEOUT,
                )
            return
        except Exception as e:
            last_error = e
            logger.warning(
                "فشلت محاولة رفع الفيديو %s (محاولة %d/%d): %s: %s",
                file_path.name, attempt, UPLOAD_MAX_RETRIES, type(e).__name__, e,
            )
            if attempt < UPLOAD_MAX_RETRIES:
                await asyncio.sleep(_upload_backoff_seconds(attempt))

    # محاولة أخيرة كمستند (نفس المنطق الموضّح في send_audio_with_retry)
    try:
        with open(file_path, "rb") as fh:
            await message.reply_document(
                document=fh,
                filename=file_path.name,
                caption=caption,
                read_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                write_timeout=TELEGRAM_UPLOAD_TIMEOUT,
                connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
                pool_timeout=TELEGRAM_POOL_TIMEOUT,
            )
        logger.info("تم إرسال %s كمستند بعد فشل الإرسال كفيديو", file_path.name)
        return
    except Exception as e:
        logger.warning("فشلت أيضاً محاولة الإرسال كمستند لـ %s: %s", file_path.name, e)

    raise last_error


class State(IntEnum):
    CONFIRM_URL = 1
    ASK_TRIM = 2
    ASK_SEP_TYPE = 3
    ASK_QUALITY = 4
    ASK_FORMAT = 5


# ---------------------------------------------------------------------------
# دوال مساعدة: تخزين مؤقت (Cache)
# ---------------------------------------------------------------------------

def _load_cache_index() -> dict:
    if CACHE_INDEX_PATH.exists():
        try:
            return json.loads(CACHE_INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache_index(index: dict):
    CACHE_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")


def make_cache_key(source_id: str, sep_type: str, quality: str, fmt: str, trim: str) -> str:
    raw = f"{source_id}|{sep_type}|{quality}|{fmt}|{trim}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def cache_get(key: str):
    """إرجاع قائمة مسارات الملفات المخزّنة مسبقاً إذا كانت موجودة وسارية الصلاحية"""
    with _CACHE_LOCK:
        index = _load_cache_index()
        entry = index.get(key)
        if not entry:
            return None
        if time.time() - entry["timestamp"] > CACHE_TTL_SECONDS:
            return None
        files = [Path(p) for p in entry["files"]]
        if files and all(f.exists() for f in files):
            return files
        return None


def cache_set(key: str, files: list):
    """نسخ الملفات الناتجة إلى مجلد الكاش الدائم وتسجيلها في الفهرس"""
    with _CACHE_LOCK:
        index = _load_cache_index()
        job_cache_dir = CACHE_DIR / key
        job_cache_dir.mkdir(parents=True, exist_ok=True)
        stored_paths = []
        for f in files:
            dest = job_cache_dir / f.name
            shutil.copy(f, dest)
            stored_paths.append(str(dest))
        index[key] = {"timestamp": time.time(), "files": stored_paths}
        _save_cache_index(index)


def cleanup_expired_cache():
    """حذف مدخلات الكاش المنتهية الصلاحية (تُستدعى عند بدء تشغيل البوت)"""
    with _CACHE_LOCK:
        index = _load_cache_index()
        now = time.time()
        expired_keys = [k for k, v in index.items() if now - v["timestamp"] > CACHE_TTL_SECONDS]
        for key in expired_keys:
            shutil.rmtree(CACHE_DIR / key, ignore_errors=True)
            del index[key]
        if expired_keys:
            _save_cache_index(index)
            logger.info("تم حذف %d مدخلة كاش منتهية الصلاحية", len(expired_keys))


# ---------------------------------------------------------------------------
# دوال مساعدة: معالجة الصوت
# ---------------------------------------------------------------------------

def format_duration(seconds) -> str:
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _ydl_network_opts() -> dict:
    """
    خيارات الشبكة المشتركة لكل نداءات yt-dlp: بروكسي منفصل (إن وُجد)، ومهلة/محاولات
    أطول لتقليل فشل تحميل المقاطع الطويلة على اتصال متوسط السرعة
    """
    opts = {"socket_timeout": YTDLP_SOCKET_TIMEOUT, "retries": YTDLP_RETRIES}
    if YTDLP_PROXY_URL:
        opts["proxy"] = YTDLP_PROXY_URL
    return opts


def get_video_info(url: str) -> dict:
    """جلب معلومات المقطع (العنوان، المدة، الصورة المصغرة، هل هو فيديو) دون تحميله"""
    ydl_opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True, "skip_download": True,
        **_ydl_network_opts(),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    vcodec = str(info.get("vcodec") or "none")
    return {
        "title": info.get("title") or url,
        "duration": info.get("duration") or 0,
        "thumbnail": info.get("thumbnail"),
        "is_video": vcodec.lower() != "none",
    }


def download_video_from_url(url: str, job_dir: Path) -> Path:
    """
    تحميل الفيديو كاملاً (الصورة + الصوت معاً) من رابط باستخدام yt-dlp
    تُستخدم عندما يكون المصدر فيديو ويريد المستخدم أن تبقى النتيجة فيديو
    """
    output_template = str(job_dir / "downloaded_video.%(ext)s")

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": output_template,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration <? {MAX_URL_DURATION_SECONDS}"),
        **_ydl_network_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    downloaded_files = list(job_dir.glob("downloaded_video.*"))
    video_files = [f for f in downloaded_files if f.suffix.lower() in (".mp4", ".mkv", ".webm")]

    if not video_files:
        raise RuntimeError(
            "تعذّر تحميل الفيديو من الرابط. تأكد أن الرابط صحيح ويشير لمقطع فيديو، "
            "وأن المقطع لا يتجاوز الحد المسموح."
        )

    return video_files[0]


def extract_audio_from_video(video_path: Path, job_dir: Path) -> Path:
    """استخراج المسار الصوتي من ملف فيديو كملف wav نظيف تمهيداً لمعالجته بواسطة Demucs"""
    dest = job_dir / "extracted_audio.wav"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل استخراج الصوت من الفيديو: {result.stderr[-300:]}")
    return dest


def trim_video_only(video_path: Path, start: str, end: str, job_dir: Path) -> Path:
    """
    قص الجزء المطلوب من المسار المرئي فقط (بدون صوت) بين وقتين محددين
    يُستخدم لإبقاء الصورة متزامنة مع الصوت المقصوص قبل إعادة دمجهما لاحقاً
    """
    dest = job_dir / "trimmed_video.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-ss", start,
        "-to", end,
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل قص الفيديو: {result.stderr[-300:]}")
    return dest


def mux_audio_with_video(video_path: Path, audio_path: Path, out_name: str, job_dir: Path) -> Path:
    """
    دمج مسار صوتي معالَج (ناتج Demucs) مع المسار المرئي الأصلي لإنتاج فيديو نهائي.

    ملاحظة مهمة: نعيد ترميز الفيديو دائماً إلى H.264 (بدل -c:v copy) لأن بعض المقاطع
    المحمّلة من الروابط تكون بترميز HEVC/H.265 أو غيره، وهذا يعمل بشكل طبيعي على معظم
    الهواتف (فك تشفير بالهاردوير) لكن كثيراً من مشغّلات اللابتوب (QuickTime القديم،
    Windows بدون إضافة الترميز) لا تدعمه، فتظهر شاشة سوداء مع بقاء الصوت شغّالاً فقط.
    H.264 + yuv420p مدعوم عملياً في كل مكان. كذلك نضيف +faststart لتشغيل أسرع وتوافق أعلى.
    """
    dest = job_dir / f"{out_name}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل دمج الصوت مع الفيديو: {result.stderr[-300:]}")
    return dest


def compress_video_if_needed(video_path: Path, max_size_mb: int) -> Path:
    """
    ضغط الفيديو تلقائياً إذا تجاوز حجمه الحد المسموح، بدل الاكتفاء بتحذير المستخدم
    السبب: نستخدم -c:v copy عند الدمج (نسخ مباشر بنفس جودة/حجم الفيديو الأصلي)، وهذا
    قد ينتج ملفات كبيرة يصعب رفعها بنجاح على اتصال بطيء أو غير مستقر. تصغير الحجم
    يقلل وقت التعرض للرفع، مما يرفع فرصة نجاحه كثيراً حتى لو ظلت الشبكة غير مثالية.

    نحسب معدل بت (bitrate) تقريبي مستهدف بناءً على مدة الفيديو والحجم المطلوب، ونعيد
    الترميز مرة واحدة بذلك المعدل بدل تجربة عدة قيم (لتوفير الوقت).
    """
    size_mb = video_path.stat().st_size / (1024 * 1024)
    if size_mb <= max_size_mb:
        return video_path

    duration = get_media_duration_seconds(video_path)
    if not duration or duration <= 0:
        duration = 60.0  # قيمة احتياطية إذا تعذّر قراءة المدة

    # نستهدف 90% من الحد المسموح لترك هامش أماناً لحاويات mp4/التغليف
    target_total_kbits = max_size_mb * 0.9 * 8192  # ميجابايت -> كيلوبت
    audio_kbps = 128
    video_kbps = max(300, int(target_total_kbits / duration) - audio_kbps)

    compressed_path = video_path.parent / f"{video_path.stem}_compressed.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-c:v", "libx264",
        "-b:v", f"{video_kbps}k",
        "-preset", "fast",
        "-c:a", "aac",
        "-b:a", f"{audio_kbps}k",
        str(compressed_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.warning("فشل ضغط الفيديو، سيُرسل بحجمه الأصلي: %s", result.stderr[-300:])
        return video_path

    logger.info(
        "تم ضغط الفيديو من %.1f MB إلى %.1f MB",
        size_mb, compressed_path.stat().st_size / (1024 * 1024),
    )
    return compressed_path


def get_media_duration_seconds(path: Path) -> float:
    """قراءة مدة ملف صوتي/فيديو بالثواني عبر ffprobe"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except (ValueError, AttributeError):
        return 0.0


def download_audio_from_url(url: str, job_dir: Path) -> Path:
    """تحميل الصوت فقط من رابط باستخدام yt-dlp"""
    output_template = str(job_dir / "downloaded.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "match_filter": yt_dlp.utils.match_filter_func(f"duration <? {MAX_URL_DURATION_SECONDS}"),
        **_ydl_network_opts(),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    downloaded_files = list(job_dir.glob("downloaded.*"))
    mp3_files = [f for f in downloaded_files if f.suffix == ".mp3"]

    if not mp3_files:
        raise RuntimeError(
            "تعذّر تحميل الصوت من الرابط. تأكد أن الرابط صحيح ويشير لمقطع يحتوي صوتاً، "
            "وأن المقطع لا يتجاوز الحد المسموح."
        )

    return mp3_files[0]


def trim_audio(input_path: Path, start: str, end: str, job_dir: Path) -> Path:
    """قص جزء من الملف الصوتي بين وقتين محددين"""
    dest = job_dir / "trimmed.mp3"
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-ss", start,
        "-to", end,
        "-acodec", "libmp3lame",
        "-qscale:a", "2",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل قص المقطع: {result.stderr[-300:]}")
    return dest


def convert_audio(src_path: Path, target_format: str, out_name: str) -> Path:
    """تحويل ملف wav الناتج من Demucs إلى الصيغة المطلوبة (mp3/wav/flac)"""
    dest = src_path.parent / f"{out_name}.{target_format}"

    if target_format == "wav":
        shutil.copy(src_path, dest)
        return dest

    codec = {"mp3": "libmp3lame", "flac": "flac"}[target_format]
    cmd = ["ffmpeg", "-y", "-i", str(src_path), "-codec:a", codec]
    if target_format == "mp3":
        cmd += ["-qscale:a", "2"]
    cmd.append(str(dest))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل تحويل الصيغة: {result.stderr[-300:]}")
    return dest


def run_demucs(input_path: Path, job_dir: Path, model: str, two_stems: Optional[str], progress_cb=None) -> dict:
    """
    تشغيل Demucs مع قراءة مخرجاته سطراً بسطر لاستخراج نسبة التقدم الفعلية
    يرجع قاموس {اسم_المسار: مسار_الملف} مثل {"vocals": Path(...), "no_vocals": Path(...)}
    أو {"vocals":..., "drums":..., "bass":..., "other":...} عند الفصل الكامل

    ملاحظتان مهمتان للأداء:
    - shifts=0: تعطيل مرحلة "التحويل العشوائي" الإضافية التي يقوم بها Demucs افتراضياً
      لتحسين الدقة قليلاً؛ تعطيلها يسرّع المعالجة تقريباً للنصف ويمنع شريط التقدم من
      الرجوع للصفر وإعادة العد (كان هذا يحدث بسبب مرور مرحلتين منفصلتين كل منهما 0-100)
    - -j: توزيع المعالجة على عدة أنوية للمعالج (CPU) بدل نواة واحدة فقط
    """
    output_dir = job_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["demucs", "-n", model, "-o", str(output_dir), "--shifts", "0"]
    if DEMUCS_JOBS > 1:
        cmd += ["-j", str(DEMUCS_JOBS)]
    if DEMUCS_SEGMENT:
        cmd += ["--segment", DEMUCS_SEGMENT]
    if two_stems:
        cmd += ["--two-stems", two_stems]
    cmd.append(str(input_path))

    logger.info("تشغيل الأمر: %s", " ".join(cmd))

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )

    buffer = ""
    tail_lines = []

    while True:
        char = process.stdout.read(1)
        if char == "":
            if process.poll() is not None:
                break
            continue
        if char in ("\r", "\n"):
            line = buffer
            buffer = ""
            if line.strip():
                tail_lines.append(line.strip())
                if len(tail_lines) > 15:
                    tail_lines.pop(0)
            match = PROGRESS_PATTERN.search(line)
            if match and progress_cb:
                percent = min(int(match.group(1)), 100)
                progress_cb(percent)
        else:
            buffer += char

    process.wait()

    if process.returncode != 0:
        # returncode = -9 (أو 137 حسب طريقة الإبلاغ) يعني قُتلت العملية بإشارة SIGKILL
        # من نظام التشغيل، وهذا شبه مؤكد بسبب نفاد الذاكرة (OOM) وليس خطأ ببيانات
        # الإدخال أو بـ Demucs نفسه — لا توجد رسالة خطأ حقيقية لأن العملية أُنهيت فجأة
        if process.returncode in (-9, 137):
            raise RuntimeError(
                "فشلت معالجة Demucs: يبدو أن العملية قُتلت بسبب نفاد الذاكرة (Out of "
                "Memory) على السيرفر — Demucs يحتاج رام كافية. جرّب: تقليل DEMUCS_JOBS "
                "إلى 1 (مُفعّل افتراضياً الآن)، استخدام خيار الجودة السريع بدل الدقيق، "
                "أو ترقية باقة الاستضافة لرام أكبر."
            )
        raise RuntimeError(
            f"فشلت معالجة Demucs (رمز الخروج {process.returncode}): "
            + " | ".join(tail_lines[-5:])
        )

    stem_dir = output_dir / model / input_path.stem
    if not stem_dir.exists():
        raise FileNotFoundError(f"لم يتم العثور على مجلد الناتج {stem_dir}")

    result = {f.stem: f for f in stem_dir.glob("*.wav")}
    if not result:
        raise FileNotFoundError(f"لم يتم إنتاج أي ملفات في {stem_dir}")

    return result


def make_progress_callback(loop: asyncio.AbstractEventLoop, status_msg, lang: str, total_passes: int = 1):
    """
    إرجاع دالة callback يتم استدعاؤها من داخل الـ thread الذي يشغّل Demucs
    لتحديث رسالة الحالة في تلجرام بنسبة تقدم إجمالية سلسة (0-100 مرة واحدة فقط
    من منظور المستخدم)، حتى لو كان Demucs يمرّ داخلياً بعدة مراحل (passes) كل
    منها تُصدر شريط تقدم منفصل من 0 إلى 100 (يحدث هذا مع نموذج "دقيق" الذي هو
    مجموعة من عدة نماذج تُطبَّق بالتتابع)

    مع تحديد التحديثات لتفادي تجاوز حدود تلجرام لعدد التعديلات المسموحة على نفس الرسالة
    """
    state = {"last_raw": -1, "pass_index": 0, "last_overall": -1, "last_time": 0.0}

    def callback(raw_percent: int):
        now = time.time()

        # اكتشاف بداية مرحلة جديدة: النسبة الخام رجعت للانخفاض بشكل كبير بعد أن
        # كانت قريبة من 100 في المرحلة السابقة
        if raw_percent < state["last_raw"] - 20:
            state["pass_index"] = min(state["pass_index"] + 1, total_passes - 1)
        state["last_raw"] = raw_percent

        overall = int(((state["pass_index"] * 100) + raw_percent) / total_passes)
        overall = max(0, min(overall, 100))

        if overall == state["last_overall"]:
            return
        # تحديث فقط كل 3 ثوانٍ على الأقل أو كل قفزة 10% لتفادي حدود تلجرام
        if overall < 100 and (now - state["last_time"] < 3) and (overall - state["last_overall"] < 10):
            return
        state["last_overall"] = overall
        state["last_time"] = now

        async def _edit():
            await safe_edit_text(status_msg, t(lang, "processing_progress", percent=overall))

        asyncio.run_coroutine_threadsafe(_edit(), loop)

    return callback


# ---------------------------------------------------------------------------
# محادثة تلجرام: نقاط الدخول
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.language_code)
    await update.message.reply_text(t(lang, "welcome"))


async def entry_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطة دخول: المستخدم أرسل ملفاً مباشرة (صوت/فيديو/مستند/رسالة صوتية)"""
    message = update.message
    lang = get_lang(update.effective_user.language_code)

    tg_file = None
    original_name = "input"
    is_video = False

    if message.audio:
        tg_file = message.audio
        original_name = tg_file.file_name or "audio.mp3"
    elif message.voice:
        tg_file = message.voice
        original_name = "voice.ogg"
    elif message.video:
        tg_file = message.video
        original_name = tg_file.file_name or "video.mp4"
        is_video = True
    elif message.document:
        tg_file = message.document
        original_name = tg_file.file_name or "file"
        is_video = bool(tg_file.mime_type) and tg_file.mime_type.startswith("video/")
    else:
        await message.reply_text(t(lang, "send_audio_error"))
        return ConversationHandler.END

    if tg_file.file_size and tg_file.file_size > MAX_FILE_SIZE:
        await message.reply_text(t(lang, "file_too_large"))
        return ConversationHandler.END

    job_id = str(uuid.uuid4())[:8]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    input_path = job_dir / original_name

    status_msg = await message.reply_text(t(lang, "downloading_file"))

    try:
        file_obj = await tg_file.get_file()
        await file_obj.download_to_drive(custom_path=str(input_path))
    except Exception as e:
        logger.exception("فشل تحميل الملف من تلجرام")
        await status_msg.edit_text(t(lang, "error_generic", error=str(e)[:300]))
        shutil.rmtree(job_dir, ignore_errors=True)
        return ConversationHandler.END

    video_path = None
    audio_input_path = input_path

    if is_video:
        await safe_edit_text(status_msg, t(lang, "extracting_audio"))
        loop = asyncio.get_running_loop()
        try:
            audio_input_path = await loop.run_in_executor(None, extract_audio_from_video, input_path, job_dir)
        except Exception as e:
            logger.exception("فشل استخراج الصوت من الفيديو")
            await status_msg.edit_text(t(lang, "error_generic", error=str(e)[:300]))
            shutil.rmtree(job_dir, ignore_errors=True)
            return ConversationHandler.END
        video_path = input_path

    context.user_data.update({
        "lang": lang,
        "job_dir": job_dir,
        "input_path": audio_input_path,
        "video_path": video_path,
        "is_video": is_video,
        "source_id": tg_file.file_unique_id,
        "trim": None,
    })

    await status_msg.edit_text(t(lang, "ask_trim"))
    context.user_data["status_msg"] = status_msg
    return State.ASK_TRIM


async def entry_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطة دخول: المستخدم أرسل رسالة نصية تحتوي رابطاً"""
    message = update.message
    lang = get_lang(update.effective_user.language_code)

    match = URL_PATTERN.search(message.text or "")
    if not match:
        await message.reply_text(t(lang, "unknown_message"))
        return ConversationHandler.END

    url = match.group(0)
    status_msg = await message.reply_text(t(lang, "downloading_url_info"))

    loop = asyncio.get_running_loop()
    try:
        info = await loop.run_in_executor(None, get_video_info, url)
    except Exception:
        logger.exception("فشل جلب معلومات الرابط")
        await status_msg.edit_text(t(lang, "url_fetch_error"))
        return ConversationHandler.END

    duration = info.get("duration", 0)
    if duration and duration > MAX_URL_DURATION_SECONDS:
        await status_msg.edit_text(
            t(lang, "duration_too_long", minutes=duration // 60, limit=MAX_URL_DURATION_SECONDS // 60)
        )
        return ConversationHandler.END

    job_id = str(uuid.uuid4())[:8]
    job_dir = WORK_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    context.user_data.update({
        "lang": lang,
        "job_dir": job_dir,
        "url": url,
        "source_id": url,
        "is_video": info.get("is_video", False),
        "trim": None,
    })

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "btn_confirm"), callback_data="confirm_url"),
        InlineKeyboardButton(t(lang, "btn_cancel"), callback_data="cancel_url"),
    ]])
    caption = t(lang, "url_preview_caption", title=info["title"][:150], duration=format_duration(duration))
    thumb = info.get("thumbnail")

    if thumb:
        try:
            await status_msg.delete()
            status_msg = await message.reply_photo(photo=thumb, caption=caption, reply_markup=keyboard)
        except Exception:
            await status_msg.edit_text(caption, reply_markup=keyboard)
    else:
        await status_msg.edit_text(caption, reply_markup=keyboard)

    context.user_data["status_msg"] = status_msg
    return State.CONFIRM_URL


# ---------------------------------------------------------------------------
# محادثة تلجرام: خطوات المتابعة
# ---------------------------------------------------------------------------

async def confirm_url_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    lang = ud["lang"]
    is_photo = bool(query.message.caption)

    async def _update_status(text: str, **kwargs):
        try:
            if is_photo:
                await query.edit_message_caption(caption=text, **kwargs)
            else:
                await query.edit_message_text(text, **kwargs)
        except Exception:
            pass

    if query.data == "cancel_url":
        await _update_status(t(lang, "cancelled"))
        shutil.rmtree(ud.get("job_dir", WORK_DIR), ignore_errors=True)
        context.user_data.clear()
        return ConversationHandler.END

    is_video = ud.get("is_video", False)
    loop = asyncio.get_running_loop()

    if is_video:
        await _update_status(t(lang, "downloading_video_from_url"))
        try:
            video_path = await loop.run_in_executor(None, download_video_from_url, ud["url"], ud["job_dir"])
        except Exception as e:
            logger.exception("فشل تحميل الفيديو من الرابط")
            await _update_status(t(lang, "error_url", error=str(e)[:300]))
            shutil.rmtree(ud["job_dir"], ignore_errors=True)
            context.user_data.clear()
            return ConversationHandler.END

        try:
            audio_path = await loop.run_in_executor(None, extract_audio_from_video, video_path, ud["job_dir"])
        except Exception as e:
            logger.exception("فشل استخراج الصوت من الفيديو")
            await _update_status(t(lang, "error_url", error=str(e)[:300]))
            shutil.rmtree(ud["job_dir"], ignore_errors=True)
            context.user_data.clear()
            return ConversationHandler.END

        ud["video_path"] = video_path
        ud["input_path"] = audio_path
    else:
        await _update_status(t(lang, "downloading_audio_from_url"))
        try:
            input_path = await loop.run_in_executor(None, download_audio_from_url, ud["url"], ud["job_dir"])
        except Exception as e:
            logger.exception("فشل تحميل الصوت من الرابط")
            await _update_status(t(lang, "error_url", error=str(e)[:300]))
            shutil.rmtree(ud["job_dir"], ignore_errors=True)
            context.user_data.clear()
            return ConversationHandler.END

        ud["video_path"] = None
        ud["input_path"] = input_path

    # نرسل رسالة نصية جديدة لخطوة القص بدل تعديل تعليق الصورة (أوضح للمستخدم)
    new_msg = await context.bot.send_message(chat_id=query.message.chat_id, text=t(lang, "ask_trim"))
    ud["status_msg"] = new_msg
    return State.ASK_TRIM


async def receive_trim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    ud = context.user_data
    lang = ud["lang"]
    text = (message.text or "").strip()

    match = TRIM_PATTERN.match(text)
    if not match:
        await message.reply_text(t(lang, "invalid_trim"))
        return State.ASK_TRIM

    start, end = match.group(1), match.group(2)
    status_msg = await message.reply_text(t(lang, "trimming_audio"))

    loop = asyncio.get_running_loop()
    try:
        trimmed_path = await loop.run_in_executor(
            None, trim_audio, ud["input_path"], start, end, ud["job_dir"]
        )
        if ud.get("video_path"):
            trimmed_video = await loop.run_in_executor(
                None, trim_video_only, ud["video_path"], start, end, ud["job_dir"]
            )
            ud["video_path"] = trimmed_video
    except Exception as e:
        logger.exception("فشل قص المقطع")
        await status_msg.edit_text(t(lang, "error_generic", error=str(e)[:300]))
        return State.ASK_TRIM

    ud["input_path"] = trimmed_path
    ud["trim"] = f"{start}-{end}"
    await status_msg.edit_text(t(lang, "trim_applied", start=start, end=end))

    return await send_sep_type_prompt(update, context)


async def skip_trim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await send_sep_type_prompt(update, context)


async def send_sep_type_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> State:
    ud = context.user_data
    lang = ud["lang"]
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_music_only"), callback_data="sep_music")],
        [InlineKeyboardButton(t(lang, "btn_vocals_only"), callback_data="sep_vocals")],
        [InlineKeyboardButton(t(lang, "btn_full_stems"), callback_data="sep_full")],
    ])
    msg = await update.effective_message.reply_text(t(lang, "ask_sep_type"), reply_markup=keyboard)
    ud["status_msg"] = msg
    return State.ASK_SEP_TYPE


async def receive_sep_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    lang = ud["lang"]

    sep_map = {"sep_music": "music", "sep_vocals": "vocals", "sep_full": "full"}
    ud["sep_type"] = sep_map[query.data]

    keyboard_rows = [[InlineKeyboardButton(t(lang, "btn_fast"), callback_data="quality_fast")]]
    # نخفي خيار "دقيق" (نموذج ensemble من عدة نماذج، يستهلك رام أضعاف الخيار السريع)
    # عند تفعيل LOW_MEMORY_MODE، لأنه شبه مضمون يسبب OOM على استضافات محدودة الرام
    if not LOW_MEMORY_MODE:
        keyboard_rows.append(
            [InlineKeyboardButton(t(lang, "btn_accurate"), callback_data="quality_accurate")]
        )
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    await query.edit_message_text(t(lang, "ask_quality"), reply_markup=keyboard)
    ud["status_msg"] = query.message
    return State.ASK_QUALITY


async def receive_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data
    lang = ud["lang"]

    ud["quality"] = "fast" if query.data == "quality_fast" else "accurate"
    ud["status_msg"] = query.message

    if ud.get("is_video"):
        # عندما يكون المصدر فيديو، النتيجة تكون فيديو دائماً (بالصورة الأصلية)
        # لذا نتخطى خطوة اختيار الصيغة (mp3/wav/flac) وننتقل مباشرة للمعالجة
        await query.edit_message_text(t(lang, "video_output_note"))
        return await run_processing_job(update, context)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t(lang, "btn_mp3"), callback_data="format_mp3")],
        [InlineKeyboardButton(t(lang, "btn_wav"), callback_data="format_wav")],
        [InlineKeyboardButton(t(lang, "btn_flac"), callback_data="format_flac")],
    ])
    await query.edit_message_text(t(lang, "ask_format"), reply_markup=keyboard)
    return State.ASK_FORMAT


async def receive_format(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    ud = context.user_data

    ud["format"] = query.data.split("_")[1]  # format_mp3 -> mp3
    ud["status_msg"] = query.message

    # لا نعدّل النص هنا؛ run_processing_job سيحدّث الرسالة بنفسه (تفادياً لتعديل نفس
    # النص مرتين متتاليتين وهو ما يسبب خطأ "Message is not modified" من تلجرام)
    return await run_processing_job(update, context)


# ---------------------------------------------------------------------------
# تنفيذ المعالجة الفعلية وإرسال النتيجة
# ---------------------------------------------------------------------------

async def run_processing_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    message = update.effective_message
    lang = ud["lang"]
    status_msg = ud["status_msg"]
    job_dir = ud["job_dir"]
    input_path = ud["input_path"]
    sep_type = ud["sep_type"]
    quality = ud["quality"]
    is_video = ud.get("is_video", False)
    video_path = ud.get("video_path")
    fmt = ud.get("format") or ("video" if is_video else "mp3")
    trim = ud.get("trim") or ""
    source_id = ud["source_id"]

    cache_key = make_cache_key(source_id, sep_type, quality, fmt, trim)
    cached_files = cache_get(cache_key)
    loop = asyncio.get_running_loop()

    try:
        if cached_files:
            await safe_edit_text(status_msg, t(lang, "cache_hit"))
            result_files = cached_files
        else:
            if job_semaphore.locked():
                await safe_edit_text(status_msg, t(lang, "queued"))

            async with job_semaphore:
                await safe_edit_text(status_msg, t(lang, "processing_start"))
                progress_cb = make_progress_callback(
                    loop, status_msg, lang, total_passes=MODEL_PASSES.get(quality, 1)
                )
                model = QUALITY_MODELS[quality]
                two_stems = "vocals" if sep_type in ("music", "vocals") else None

                stems = await loop.run_in_executor(
                    None, run_demucs, input_path, job_dir, model, two_stems, progress_cb
                )

                await safe_edit_text(status_msg, t(lang, "preparing_final"))

                result_files = []
                if is_video:
                    # دمج كل مسار صوتي ناتج مع الصورة الأصلية لإنتاج فيديو نهائي
                    if sep_type == "music":
                        out = await loop.run_in_executor(
                            None, mux_audio_with_video, video_path, stems["no_vocals"], "video_music_only", job_dir
                        )
                        result_files = [out]
                    elif sep_type == "vocals":
                        out = await loop.run_in_executor(
                            None, mux_audio_with_video, video_path, stems["vocals"], "video_vocals_only", job_dir
                        )
                        result_files = [out]
                    else:  # full
                        for stem_key, path in stems.items():
                            out = await loop.run_in_executor(
                                None, mux_audio_with_video, video_path, path, f"video_{stem_key}", job_dir
                            )
                            result_files.append(out)

                    # ضغط تلقائي لأي فيديو ناتج تجاوز الحد المسموح، لتقليل احتمال فشل
                    # الرفع بسبب بطء/عدم استقرار الاتصال أثناء نقل ملف كبير
                    compressed_files = []
                    for f in result_files:
                        compressed = await loop.run_in_executor(
                            None, compress_video_if_needed, f, MAX_VIDEO_SEND_SIZE_MB
                        )
                        compressed_files.append(compressed)
                    result_files = compressed_files
                else:
                    if sep_type == "music":
                        out = await loop.run_in_executor(
                            None, convert_audio, stems["no_vocals"], fmt, "music_only"
                        )
                        result_files = [out]
                    elif sep_type == "vocals":
                        out = await loop.run_in_executor(
                            None, convert_audio, stems["vocals"], fmt, "vocals_only"
                        )
                        result_files = [out]
                    else:  # full
                        for stem_key, path in stems.items():
                            out = await loop.run_in_executor(None, convert_audio, path, fmt, stem_key)
                            result_files.append(out)

                cache_set(cache_key, result_files)

        chat_action = ChatAction.UPLOAD_VIDEO if is_video else ChatAction.UPLOAD_DOCUMENT
        await context.bot.send_chat_action(chat_id=message.chat_id, action=chat_action)

        # تحذير فقط إذا بقي الفيديو كبيراً رغم محاولة الضغط التلقائي (حالة نادرة)
        if is_video:
            for f in result_files:
                size_mb = f.stat().st_size / (1024 * 1024)
                if size_mb > MAX_VIDEO_SEND_SIZE_MB:
                    await message.reply_text(t(lang, "video_too_large_warning", size_mb=round(size_mb, 1)))
                    break

        for f in result_files:
            stem_for_caption = f.stem.removeprefix("video_") if is_video else f.stem
            if sep_type == "music":
                caption = t(lang, "caption_music_only")
            elif sep_type == "vocals":
                caption = t(lang, "caption_vocals_only")
            else:
                caption = t(lang, "caption_stem", stem=stem_name(lang, stem_for_caption))

            if is_video:
                await send_video_with_retry(message, f, caption)
            else:
                await send_audio_with_retry(message, f, caption)

        await status_msg.delete()

    except Exception as e:
        logger.exception("خطأ أثناء المعالجة")
        try:
            await safe_edit_text(status_msg, t(lang, "error_generic", error=str(e)[:300]))
        except Exception:
            await message.reply_text(t(lang, "error_generic", error=str(e)[:300]))

    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
        context.user_data.clear()

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# إلغاء المحادثة وانتهاء المهلة
# ---------------------------------------------------------------------------

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    lang = ud.get("lang", DEFAULT_LANG)
    job_dir = ud.get("job_dir")
    if job_dir:
        shutil.rmtree(job_dir, ignore_errors=True)
    context.user_data.clear()
    await update.effective_message.reply_text(t(lang, "cancelled"))
    return ConversationHandler.END


async def conversation_timeout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    job_dir = ud.get("job_dir")
    if job_dir:
        shutil.rmtree(job_dir, ignore_errors=True)
    context.user_data.clear()
    return ConversationHandler.END


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(update.effective_user.language_code)
    await update.message.reply_text(t(lang, "unknown_message"))


# ---------------------------------------------------------------------------
# نقطة التشغيل الرئيسية
# ---------------------------------------------------------------------------

def build_app():
    """بناء تطبيق تلجرام وتسجيل كل المعالجات؛ يُستدعى من جديد عند كل محاولة اتصال"""
    # نبني كائن HTTPXRequest مخصصاً بدل ترك القيم الافتراضية، لأن المكتبة تستخدم داخلياً
    # مهلة "media_write_timeout" منفصلة (افتراضياً 20 ثانية فقط!) عند رفع أي ملف
    # (صوت/فيديو)، وهي غالباً السبب الحقيقي وراء انقطاع الاتصال (httpx.ReadError)
    # عند رفع فيديوهات كبيرة على اتصال بطيء أو غير مستقر — حتى لو مررنا write_timeout
    # يدوياً في كل نداء reply_video/reply_audio، القيمة الافتراضية القصيرة لهذا المجمّع
    # قد تُستخدم في مسارات أخرى. كذلك pool_timeout الافتراضي (1 ثانية) قصير جداً.
    request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT,
        write_timeout=TELEGRAM_READ_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        media_write_timeout=TELEGRAM_MEDIA_WRITE_TIMEOUT,
        connection_pool_size=8,
        proxy=TELEGRAM_PROXY_URL or None,
    )

    # اتصال getUpdates (الاستطلاع الطويل) يحتاج كائن HTTPXRequest منفصلاً بمهلة قراءة
    # أطول (لأنه يبقى مفتوحاً ينتظر تحديثات جديدة). لا يمكن استخدام get_updates_proxy()
    # مع تمرير كائن request مخصص معاً؛ لذا نبني كائناً ثانياً بنفس البروكسي صراحة
    get_updates_request = HTTPXRequest(
        connect_timeout=TELEGRAM_CONNECT_TIMEOUT,
        read_timeout=TELEGRAM_READ_TIMEOUT + 10,
        write_timeout=TELEGRAM_READ_TIMEOUT,
        pool_timeout=TELEGRAM_POOL_TIMEOUT,
        connection_pool_size=4,
        proxy=TELEGRAM_PROXY_URL or None,
    )

    if TELEGRAM_PROXY_URL:
        logger.info("استخدام proxy للاتصال بتلجرام: %s", TELEGRAM_PROXY_URL)

    builder = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
    )

    app = builder.build()

    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.AUDIO | filters.VOICE | filters.VIDEO | filters.Document.ALL,
                entry_file,
            ),
            MessageHandler(
                filters.TEXT & filters.Regex(URL_PATTERN) & ~filters.COMMAND,
                entry_url,
            ),
        ],
        states={
            State.CONFIRM_URL: [
                CallbackQueryHandler(confirm_url_callback, pattern="^(confirm|cancel)_url$"),
            ],
            State.ASK_TRIM: [
                CommandHandler("skip", skip_trim),
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_trim),
            ],
            State.ASK_SEP_TYPE: [
                CallbackQueryHandler(receive_sep_type, pattern="^sep_"),
            ],
            State.ASK_QUALITY: [
                CallbackQueryHandler(receive_quality, pattern="^quality_"),
            ],
            State.ASK_FORMAT: [
                CallbackQueryHandler(receive_format, pattern="^format_"),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, conversation_timeout_handler),
                CallbackQueryHandler(conversation_timeout_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        conversation_timeout=600,  # 10 دقائق قبل إلغاء المحادثة تلقائياً إن تركها المستخدم
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.ALL, unknown_message))

    return app


def check_required_binaries():
    """
    يتحقق من وجود ffmpeg/ffprobe بمسار PATH قبل بدء التشغيل. غيابهما شائع تحديداً
    على منصات الاستضافة الجاهزة (Railway/Render/Heroku) التي لا تثبّتهما افتراضياً،
    فنعطي رسالة واضحة الآن بدل فشل غامض لاحقاً بمنتصف معالجة أول طلب من مستخدم
    """
    missing = [b for b in ("ffmpeg", "ffprobe") if shutil.which(b) is None]
    if missing:
        raise SystemExit(
            "❌ البرنامج المطلوب غير مثبّت على هذا السيرفر: " + ", ".join(missing) + "\n"
            "البوت يعتمد عليه لدمج/قياس/ضغط الفيديو والصوت. على استضافات جاهزة مثل "
            "Railway/Render/Heroku، الحل الأسهل هو النشر عبر Dockerfile (يثبّته تلقائياً)."
        )


def main():
    # علامة تحقق مؤقتة: إذا ما شفت هذا السطر بالضبط بسجلات Railway عند بدء التشغيل،
    # فهذا يعني السيرفر لسا يشغّل نسخة قديمة من الكود ولم يُنشَر التحديث فعلياً بعد
    logger.info("### BOT_CODE_VERSION_CHECK: low-memory-fix-2026-09-15 ###")
    check_required_binaries()

    if BOT_TOKEN == "ضع_توكن_البوت_هنا" or not BOT_TOKEN:
        raise SystemExit("الرجاء ضبط متغير البيئة BOT_TOKEN بتوكن البوت الخاص بك من @BotFather")

    cleanup_expired_cache()

    attempt = 0
    while True:
        attempt += 1
        app = build_app()
        try:
            logger.info(
                "البوت يعمل الآن... (MAX_CONCURRENT_JOBS=%d, محاولة اتصال رقم %d)",
                MAX_CONCURRENT_JOBS, attempt,
            )
            app.run_polling()
            break  # خروج طبيعي (مثلاً Ctrl+C) وليس بسبب خطأ
        except (TimedOut, NetworkError) as e:
            if attempt >= STARTUP_MAX_RETRIES:
                logger.error(
                    "تعذّر الاتصال بتلجرام بعد %d محاولة. تأكد من اتصالك بالإنترنت أو "
                    "استخدم TELEGRAM_PROXY_URL إذا كان تلجرام محجوباً في شبكتك.",
                    attempt,
                )
                raise
            logger.warning(
                "فشل الاتصال بتلجرام (محاولة %d/%d): %s — إعادة المحاولة خلال %d ثانية...",
                attempt, STARTUP_MAX_RETRIES, e, STARTUP_RETRY_DELAY,
            )
            time.sleep(STARTUP_RETRY_DELAY)


if __name__ == "__main__":
    main()
