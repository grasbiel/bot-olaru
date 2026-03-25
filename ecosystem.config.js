module.exports = {
  apps : [{
    name: "olaru-bot",
    script: "venv/Scripts/python.exe",
    args: "-m uvicorn main:app --host 0.0.0.0 --port 8000",
    instances: 1,
    autorestart: True,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: "production",
    }
  }]
}
