FROM python:3.11-slim

# نصّب ffmpeg على مستوى نظام التشغيل — هذا هو الجزء المفقود على منصات الاستضافة
# الجاهزة (Railway/Render/Heroku) التي لا تثبّته تلقائياً بيئتها الافتراضية.
# البوت يعتمد على ffmpeg/ffprobe في عدة أماكن: دمج الفيديو مع الصوت المعالَج،
# قياس مدة المقاطع، ضغط الفيديو، وأيضاً تدمج بعض صيغ yt-dlp عبره.
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ننسخ requirements.txt أولاً بمفرده حتى تستفيد Docker من الكاش (لا يعيد تثبيت كل
# شيء إلا إذا تغيّرت المتطلبات فعلاً، لا كل مرة يتغيّر فيها كود بايثون)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# البوت يعمل بنظام Long Polling (getUpdates) وليس Webhook، فلا حاجة لفتح أي منفذ
CMD ["python", "bot.py"]
