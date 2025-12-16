#!/bin/bash

# Default to Turbo if not set
APP_TYPE="${APP_TYPE:-turbo}"

echo "Starting Chatterbox Container..."
echo "Selected App Type: $APP_TYPE"

if [ "$APP_TYPE" = "turbo" ]; then
    echo "Launching Gradio Turbo App..."
    python gradio_tts_turbo_app.py
elif [ "$APP_TYPE" = "standard" ]; then
    echo "Launching Gradio Standard App..."
    python gradio_tts_app.py
elif [ "$APP_TYPE" = "multilingual" ]; then
    echo "Launching Multilingual App..."
    python multilingual_app.py
elif [ "$APP_TYPE" = "vc" ]; then
    echo "Launching Voice Conversion App..."
    python gradio_vc_app.py
else
    echo "Unknown APP_TYPE. Defaulting to Turbo."
    python gradio_tts_turbo_app.py
fi
