#!/bin/bash

# 1. Docker konteynerlerini ayağa kaldır
echo "Servisler başlatılıyor..."
docker-compose up -d --build

# 2. Hosttaki Ollama'nın çalışıp çalışmadığını kontrol et
echo "Ollama ve Model kontrol ediliyor..."

# Ollama yüklü mü?
if ! command -v ollama &> /dev/null; then
    echo "HATA: 'ollama' komutu bulunamadı!"
    echo "Lütfen https://ollama.com adresinden Ollama'yı indirip kurun."
    echo "Kurulumdan sonra bu scripti tekrar çalıştırın."
    exit 1
fi

# Ollama çalışıyor mu? (Servis ayakta mı?)
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "UYARI: Ollama servisi cevap vermiyor. Başlatılıyor..."
    ollama serve &
    OLLAMA_PID=$!
    # Servisin başlamasını bekle
    sleep 5
fi

# 3. Gerekli modeli hosttaki Ollama'ya çektir
echo "Llama3 modeli kontrol ediliyor/indiriliyor..."
curl http://localhost:11434/api/pull -d '{"name": "llama3"}'

echo "Sistem hazır! http://localhost:5003 üzerinden istek atabilirsiniz."
