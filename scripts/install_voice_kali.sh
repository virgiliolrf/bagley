#!/usr/bin/env bash
# Install script pra voice stack do Bagley em Kali Linux (ARM64 ou x86_64).
# Testa existência antes de instalar pra ser idempotente.

set -euo pipefail

echo "[bagley-install] apt dependencies"
sudo apt update
sudo apt install -y \
    alsa-utils \
    portaudio19-dev \
    python3-dev \
    python3-pip \
    build-essential \
    ffmpeg \
    curl \
    wget \
    tesseract-ocr

# Piper (binário oficial, ARM64 ou amd64)
if ! command -v piper &> /dev/null; then
    echo "[bagley-install] piper-tts binary"
    ARCH=$(uname -m)
    case "$ARCH" in
        x86_64)  PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz" ;;
        aarch64|arm64) PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_aarch64.tar.gz" ;;
        armv7l)  PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_armv7l.tar.gz" ;;
        *) echo "arch $ARCH não suportado"; exit 1 ;;
    esac
    mkdir -p ~/.local/bin
    cd /tmp
    curl -L "$PIPER_URL" -o piper.tar.gz
    tar xzf piper.tar.gz
    sudo cp -r piper/* /usr/local/
    sudo ln -sf /usr/local/piper /usr/local/bin/piper 2>/dev/null || true
    cd -
fi

# Voz britânica (Alan)
VOICE_DIR="./models/voice"
mkdir -p "$VOICE_DIR"
if [ ! -f "$VOICE_DIR/en_GB-alan-medium.onnx" ]; then
    echo "[bagley-install] baixando voz en_GB-alan-medium"
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx" \
        -o "$VOICE_DIR/en_GB-alan-medium.onnx"
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json" \
        -o "$VOICE_DIR/en_GB-alan-medium.onnx.json"
fi

# Python deps — em venv se disponível, senão --user
echo "[bagley-install] pip deps (voice)"
PIP=${PIP:-pip3}
$PIP install --user \
    openwakeword \
    faster-whisper \
    sounddevice \
    numpy \
    webrtcvad-wheels \
    pytesseract \
    mss \
    imagehash \
    pillow

# Ollama (Linux install script oficial)
if ! command -v ollama &> /dev/null; then
    echo "[bagley-install] ollama"
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Teste rápido de áudio
echo "[bagley-install] verificando áudio..."
echo "test" | piper --model "$VOICE_DIR/en_GB-alan-medium.onnx" --output_raw 2>/dev/null | \
    aplay -q -r 22050 -f S16_LE -t raw - 2>/dev/null && \
    echo "[bagley-install] OK — you should have heard 'test'" || \
    echo "[bagley-install] WARN — áudio não produziu som, verifique ALSA/PulseAudio"

echo "[bagley-install] done."
echo ""
echo "Próximos passos:"
echo "  1. ollama create bagley -f Modelfile  (depois do deploy GGUF)"
echo "  2. python -m bagley.voice.daemon --engine ollama --allow-rfc1918"
