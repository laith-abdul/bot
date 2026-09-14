# -*- coding: utf-8 -*-
"""
ملف الترجمات (i18n) — يدعم العربية والإنجليزية والكردية (سوراني)
اللغة الافتراضية عند عدم التعرف على لغة المستخدم هي العربية
"""

LANGS = {
    "ar": {
        "welcome": (
            "أهلاً بك 👋\n\n"
            "أرسل لي أي أغنية بإحدى الطريقتين:\n"
            "1️⃣ ملف صوتي (mp3/wav/m4a) أو فيديو قصير\n"
            "2️⃣ رابط أغنية (يوتيوب، تيك توك، إنستقرام، فيسبوك، ساوندكلاود...)\n\n"
            "بعدها سأسألك عن نوع الفصل والجودة والصيغة قبل المعالجة 🎶"
        ),
        "send_audio_error": "الرجاء إرسال ملف صوتي أو فيديو يحتوي على أغنية.",
        "file_too_large": (
            "⚠️ الملف أكبر من 20 ميجابايت وهو الحد الأقصى لبوتات تلجرام العادية.\n"
            "الرجاء إرسال ملف أصغر، أو رابط بدلاً منه."
        ),
        "downloading_file": "⏳ جارٍ تحميل الملف...",
        "downloading_url_info": "🔎 جارٍ جلب معلومات الرابط...",
        "url_preview_caption": "🎬 {title}\n⏱ المدة: {duration}\n\nهل تريد المتابعة؟",
        "btn_confirm": "✅ متابعة",
        "btn_cancel": "❌ إلغاء",
        "cancelled": "تم الإلغاء.",
        "url_fetch_error": "❌ تعذّر جلب معلومات هذا الرابط. تأكد أنه صحيح ويحتوي صوتاً/فيديو.",
        "duration_too_long": "⚠️ مدة المقطع ({minutes} دقيقة) أطول من الحد المسموح ({limit} دقيقة).",
        "ask_trim": (
            "✂️ هل تريد قص جزء معين من المقطع؟\n"
            "أرسل الوقت بصيغة mm:ss-mm:ss مثال: 00:30-01:45\n"
            "أو أرسل /skip لمعالجة المقطع كاملاً."
        ),
        "invalid_trim": "⚠️ صيغة غير صحيحة. استخدم mm:ss-mm:ss مثل 00:30-01:45، أو أرسل /skip.",
        "trim_applied": "✂️ سيتم قص المقطع من {start} إلى {end}.",
        "ask_sep_type": "🎛 اختر نوع الفصل المطلوب:",
        "btn_music_only": "🎵 الموسيقى فقط",
        "btn_vocals_only": "🎤 صوت المغني فقط",
        "btn_full_stems": "🎚 فصل كامل (طبول/باص/آلات/صوت)",
        "ask_quality": "⚙️ اختر جودة المعالجة:",
        "btn_fast": "⚡ سريع (جودة جيدة)",
        "btn_accurate": "🏆 دقيق (أبطأ، جودة أعلى)",
        "ask_format": "📦 اختر صيغة الملف الناتج:",
        "btn_mp3": "MP3 (حجم أصغر)",
        "btn_wav": "WAV (جودة كاملة)",
        "btn_flac": "FLAC (بدون فقد جودة)",
        "downloading_audio_from_url": "⬇️ جارٍ تحميل الصوت من الرابط...",
        "trimming_audio": "✂️ جارٍ قص المقطع المطلوب...",
        "processing_progress": "🎧 جارٍ فصل الصوت... {percent}%",
        "processing_start": "🎧 جارٍ فصل الصوت عن الموسيقى... قد يستغرق هذا بعض الوقت.",
        "preparing_final": "🔄 جارٍ تجهيز الملف النهائي...",
        "cache_hit": "⚡ وجدت نتيجة محفوظة مسبقاً لنفس الطلب، سيتم الإرسال فوراً.",
        "queued": "⏳ طلبك في قائمة الانتظار (يوجد طلبات أخرى قيد المعالجة)...",
        "caption_music_only": "🎶 الموسيقى بدون صوت المغني",
        "caption_vocals_only": "🎤 صوت المغني فقط",
        "caption_stem": "🎚 المسار: {stem}",
        "error_generic": "❌ حدث خطأ أثناء المعالجة:\n{error}",
        "error_url": "❌ حدث خطأ أثناء معالجة الرابط:\n{error}",
        "unknown_message": "الرجاء إرسال ملف صوتي (أغنية)، أو رابط أغنية، أو استخدم /start لمعرفة طريقة الاستخدام.",
        "stems": {"vocals": "صوت", "drums": "طبول", "bass": "باص", "other": "آلات أخرى"},
    },
    "en": {
        "welcome": (
            "Welcome 👋\n\n"
            "Send me a song in one of two ways:\n"
            "1️⃣ An audio file (mp3/wav/m4a) or a short video\n"
            "2️⃣ A song link (YouTube, TikTok, Instagram, Facebook, SoundCloud...)\n\n"
            "I'll then ask you about separation type, quality, and format before processing 🎶"
        ),
        "send_audio_error": "Please send an audio file or a video containing a song.",
        "file_too_large": (
            "⚠️ The file is larger than 20MB, the limit for regular Telegram bots.\n"
            "Please send a smaller file, or a link instead."
        ),
        "downloading_file": "⏳ Downloading the file...",
        "downloading_url_info": "🔎 Fetching link info...",
        "url_preview_caption": "🎬 {title}\n⏱ Duration: {duration}\n\nContinue?",
        "btn_confirm": "✅ Continue",
        "btn_cancel": "❌ Cancel",
        "cancelled": "Cancelled.",
        "url_fetch_error": "❌ Couldn't fetch info for this link. Make sure it's valid and contains audio/video.",
        "duration_too_long": "⚠️ Duration ({minutes} min) exceeds the allowed limit ({limit} min).",
        "ask_trim": (
            "✂️ Do you want to trim a specific part?\n"
            "Send the time as mm:ss-mm:ss, e.g. 00:30-01:45\n"
            "Or send /skip to process the full track."
        ),
        "invalid_trim": "⚠️ Invalid format. Use mm:ss-mm:ss like 00:30-01:45, or send /skip.",
        "trim_applied": "✂️ The track will be trimmed from {start} to {end}.",
        "ask_sep_type": "🎛 Choose the separation type:",
        "btn_music_only": "🎵 Music only",
        "btn_vocals_only": "🎤 Vocals only",
        "btn_full_stems": "🎚 Full split (drums/bass/other/vocals)",
        "ask_quality": "⚙️ Choose processing quality:",
        "btn_fast": "⚡ Fast (good quality)",
        "btn_accurate": "🏆 Accurate (slower, higher quality)",
        "ask_format": "📦 Choose output format:",
        "btn_mp3": "MP3 (smaller size)",
        "btn_wav": "WAV (full quality)",
        "btn_flac": "FLAC (lossless)",
        "downloading_audio_from_url": "⬇️ Downloading audio from the link...",
        "trimming_audio": "✂️ Trimming the requested part...",
        "processing_progress": "🎧 Separating audio... {percent}%",
        "processing_start": "🎧 Separating vocals from music... this may take a while.",
        "preparing_final": "🔄 Preparing the final file...",
        "cache_hit": "⚡ Found a cached result for the same request, sending now.",
        "queued": "⏳ Your request is queued (other jobs are processing)...",
        "caption_music_only": "🎶 Music without vocals",
        "caption_vocals_only": "🎤 Vocals only",
        "caption_stem": "🎚 Stem: {stem}",
        "error_generic": "❌ An error occurred while processing:\n{error}",
        "error_url": "❌ An error occurred while processing the link:\n{error}",
        "unknown_message": "Please send an audio file, a song link, or use /start to see how it works.",
        "stems": {"vocals": "Vocals", "drums": "Drums", "bass": "Bass", "other": "Other"},
    },
    "ku": {
        # کوردیی سۆرانی (وەرگێڕانێکی سادەیە، ڕاستکردنەوەی داواکراوە بۆ باشترکردن)
        "welcome": (
            "بەخێربێیت 👋\n\n"
            "گۆرانیەک بنێرە بەم دوو شێوەیە:\n"
            "1️⃣ فایلی دەنگ (mp3/wav/m4a) یان ڤیدیۆیەکی کورت\n"
            "2️⃣ لینکی گۆرانی (یوتیوب، تیک تۆک، ئینستاگرام، فەیسبووک، ساوندکلاود...)\n\n"
            "پاشان پرسیارت لێ دەکەم دەربارەی جۆری جیاکردنەوە و کوالیتی و فۆرمات پێش پرۆسەکردن 🎶"
        ),
        "send_audio_error": "تکایە فایلێکی دەنگ یان ڤیدیۆیەک کە گۆرانی تێدایە بنێرە.",
        "file_too_large": (
            "⚠️ فایلەکە گەورەترە لە 20 مێگابایت کە سنووری ڕۆبۆتی ئاساییی تلگرامە.\n"
            "تکایە فایلێکی بچووکتر یان لینکێک بنێرە."
        ),
        "downloading_file": "⏳ فایلەکە دادەبەزێت...",
        "downloading_url_info": "🔎 زانیاری لینکەکە وەردەگیرێت...",
        "url_preview_caption": "🎬 {title}\n⏱ ماوە: {duration}\n\nبەردەوام بیت؟",
        "btn_confirm": "✅ بەردەوامبوون",
        "btn_cancel": "❌ هەڵوەشاندنەوە",
        "cancelled": "هەڵوەشێنرایەوە.",
        "url_fetch_error": "❌ نەتوانرا زانیاری ئەم لینکە وەربگیرێت. دڵنیابەرەوە کە درووستە.",
        "duration_too_long": "⚠️ ماوەکە ({minutes} خولەک) لە سنووری ڕێگەپێدراو ({limit} خولەک) زیاترە.",
        "ask_trim": (
            "✂️ دەتەوێت بەشێکی دیاریکراو کورت بکەیتەوە؟\n"
            "کاتەکە بنێرە بەم شێوەیە mm:ss-mm:ss نموونە: 00:30-01:45\n"
            "یان /skip بنێرە بۆ پرۆسەکردنی هەموو گۆرانیەکە."
        ),
        "invalid_trim": "⚠️ فۆرماتەکە هەڵەیە. mm:ss-mm:ss بەکاربهێنە وەک 00:30-01:45، یان /skip بنێرە.",
        "trim_applied": "✂️ گۆرانیەکە لە {start} بۆ {end} کورت دەکرێتەوە.",
        "ask_sep_type": "🎛 جۆری جیاکردنەوە هەڵبژێرە:",
        "btn_music_only": "🎵 تەنها میوزیک",
        "btn_vocals_only": "🎤 تەنها دەنگی گۆرانیبێژ",
        "btn_full_stems": "🎚 جیاکردنەوەی تەواو (درام/بەیس/ئامێر/دەنگ)",
        "ask_quality": "⚙️ کوالیتی پرۆسەکردن هەڵبژێرە:",
        "btn_fast": "⚡ خێرا (کوالیتی باش)",
        "btn_accurate": "🏆 وردبین (هێواشترە، کوالیتی بەرزتر)",
        "ask_format": "📦 فۆرماتی دەرچوو هەڵبژێرە:",
        "btn_mp3": "MP3 (قەبارەی بچووکتر)",
        "btn_wav": "WAV (کوالیتی تەواو)",
        "btn_flac": "FLAC (بێ لەدەستدانی کوالیتی)",
        "downloading_audio_from_url": "⬇️ دەنگ لە لینکەکە دادەبەزێت...",
        "trimming_audio": "✂️ بەشە داواکراوەکە کورت دەکرێتەوە...",
        "processing_progress": "🎧 دەنگ جیا دەکرێتەوە... {percent}%",
        "processing_start": "🎧 دەنگی گۆرانیبێژ لە میوزیک جیا دەکرێتەوە... کەمێک کات دەخایەنێت.",
        "preparing_final": "🔄 فایلی کۆتایی ئامادە دەکرێت...",
        "cache_hit": "⚡ ئەنجامێکی پاشەکەوتکراو بۆ هەمان داواکاری دۆزرایەوە، ڕاستەوخۆ دەنێردرێت.",
        "queued": "⏳ داواکاریەکەت لە ڕیزدایە (داواکاری تر لە پرۆسەدایە)...",
        "caption_music_only": "🎶 میوزیک بێ دەنگی گۆرانیبێژ",
        "caption_vocals_only": "🎤 تەنها دەنگی گۆرانیبێژ",
        "caption_stem": "🎚 بەش: {stem}",
        "error_generic": "❌ هەڵەیەک ڕوویدا لە کاتی پرۆسەکردن:\n{error}",
        "error_url": "❌ هەڵەیەک ڕوویدا لە کاتی پرۆسەکردنی لینکەکە:\n{error}",
        "unknown_message": "تکایە فایلێکی دەنگ یان لینکی گۆرانی بنێرە، یان /start بەکاربهێنە.",
        "stems": {"vocals": "دەنگ", "drums": "درام", "bass": "بەیس", "other": "ئامێرەکانی تر"},
    },
}

DEFAULT_LANG = "ar"


def get_lang(language_code: str | None) -> str:
    """تحديد اللغة المناسبة بناءً على كود لغة تلجرام للمستخدم"""
    if not language_code:
        return DEFAULT_LANG
    code = language_code.lower()[:2]
    if code in LANGS:
        return code
    return DEFAULT_LANG


def t(lang: str, key: str, **kwargs) -> str:
    """إرجاع النص المترجم مع تعويض القيم، مع رجوع تلقائي للعربية إذا النص غير موجود"""
    lang_dict = LANGS.get(lang, LANGS[DEFAULT_LANG])
    text = lang_dict.get(key, LANGS[DEFAULT_LANG].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def stem_name(lang: str, stem: str) -> str:
    lang_dict = LANGS.get(lang, LANGS[DEFAULT_LANG])
    return lang_dict.get("stems", {}).get(stem, stem)
